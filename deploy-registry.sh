#!/bin/bash
set -euo pipefail

# Registry-aware production deploy script for svitlo-power.
#
# Usage:
#   Deploy normally: ./deploy-registry.sh /path/to/deploy
#   Restore last backup: ./deploy-registry.sh /path/to/deploy --restore
#   Deploy to stored path: ./deploy-registry.sh
#   Restore to stored path: ./deploy-registry.sh --restore
#
# Reads registry credentials from .env.production (loaded into memory only,
# never written to disk). Falls back to local build (deploy.sh) if any
# registry pull fails.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

DEST_FILE="$REPO_ROOT/.deploy_dest"

# --- Determine action (--restore may be $1 or $2) -------------------------
ACTION="deploy"
for arg in "$@"; do
    if [ "$arg" == "--restore" ]; then
        ACTION="--restore"
        break
    fi
done

# --- Determine deploy path -------------------------------------------------
if [ "$#" -ge 1 ] && [ "${1:0:1}" != "-" ]; then
    DEPLOY_PATH="$1"
    printf '%s\n' "$DEPLOY_PATH" > "$DEST_FILE"
    echo "Stored deploy path: $DEPLOY_PATH"
else
    if [ -f "$DEST_FILE" ]; then
        DEPLOY_PATH="$(head -n1 "$DEST_FILE")"
        echo "Using stored deploy path: $DEPLOY_PATH"
    else
        echo "Error: Deployment path is required!"
        echo "Usage: $0 /path/to/deploy [--restore]"
        exit 1
    fi
fi

if [ -z "$DEPLOY_PATH" ]; then
    echo "Error: Deploy path is empty."
    exit 1
fi

BACKUP_SCRIPT="./backup.sh"
MAX_BACKUPS=7

# --- Restore path ----------------------------------------------------------
if [ "$ACTION" == "--restore" ]; then
    if [ -x "$BACKUP_SCRIPT" ]; then
        echo "Restoring last backup for $DEPLOY_PATH..."
        "$BACKUP_SCRIPT" "$DEPLOY_PATH" restore || { echo "Restore failed"; exit 1; }
        echo "Restore completed successfully."
    else
        echo "Backup script $BACKUP_SCRIPT not found or not executable. Cannot restore."
        exit 1
    fi
    exit 0
fi

# --- Backup ---------------------------------------------------------------
if [ -x "$BACKUP_SCRIPT" ]; then
    echo "Running backup script..."
    "$BACKUP_SCRIPT" "$DEPLOY_PATH" "$MAX_BACKUPS" || { echo "Backup failed"; exit 1; }
else
    echo "Backup script $BACKUP_SCRIPT not found or not executable. Skipping backup."
fi

# --- Load production environment (registry credentials + app settings) ----
ENV_FILE="$REPO_ROOT/.env.production"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env.production not found. Cannot deploy with registry."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

# Load env vars into memory only (set -a exports all, set +a disables).
set -a
# shellcheck source=/dev/null
source "$ENV_FILE"
set +a

# --- Registry login --------------------------------------------------------
if [ -z "${REGISTRY_URL:-}" ] || [ -z "${REGISTRY_USERNAME:-}" ] || [ -z "${REGISTRY_PASSWORD:-}" ]; then
    echo "Error: REGISTRY_URL, REGISTRY_USERNAME, or REGISTRY_PASSWORD not set in .env.production."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

echo "Logging in to registry $REGISTRY_URL..."
if ! docker login "$REGISTRY_URL" -u "$REGISTRY_USERNAME" -p "$REGISTRY_PASSWORD"; then
    echo "Error: Registry login failed."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

# --- Pull images -----------------------------------------------------------
# Failure here is intentionally hard. `deploy-registry.sh` does NOT
# silently fall back to an older tag — every deploy must run the
# exact image the latest CI build produced (`:latest` is re-pushed by
# every workflow). If `:latest` is missing, the registry is out of
# sync with `main` and the deploy must fail so the operator notices.
#
# The cleanup action explicitly protects `:latest` (plus the tags
# each workflow just pushed), so a missing `:latest` means the build
# workflow itself failed or was invalid — fix the workflow, do not
# paper over it here.
echo "Pulling backend images..."
if ! docker pull "$REGISTRY_URL/svitlo-power-api:latest"; then
    echo "Error: Failed to pull svitlo-power-api:latest from $REGISTRY_URL."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

if ! docker pull "$REGISTRY_URL/svitlo-power-sse-api:latest"; then
    echo "Error: Failed to pull svitlo-power-sse-api:latest from $REGISTRY_URL."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

if ! docker pull "$REGISTRY_URL/svitlo-power-grid-reporter:latest"; then
    echo "Error: Failed to pull svitlo-power-grid-reporter:latest from $REGISTRY_URL."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

echo "Pulling UI image..."
if ! docker pull "$REGISTRY_URL/svitlo-power-ui:latest"; then
    echo "Error: Failed to pull svitlo-power-ui:latest from $REGISTRY_URL."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

# --- Stop existing containers ---------------------------------------------
echo "Stopping existing containers..."
docker compose down || { echo "Failed to stop containers"; exit 1; }

# --- Start containers with pulled images ----------------------------------
echo "Starting containers with registry images..."
docker compose up -d || { echo "Failed to start containers"; exit 1; }

echo "Deployment successful!"

# --- Cleanup ---------------------------------------------------------------
echo "Cleaning up unused Docker resources..."
docker container prune -f
docker image prune -a -f
echo "Cleanup complete."