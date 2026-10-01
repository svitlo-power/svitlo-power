#!/bin/bash
set -euo pipefail

# Registry-aware production deploy script for svitlo-power.
#
# Usage:
#   Deploy normally: ./deploy-registry.sh
#   Deploy with custom tag: ./deploy-registry.sh v1.2.3
#
# Reads registry credentials from .env (loaded by docker-compose).
# Falls back to local build (deploy.sh) if any registry pull fails.
#
# Images pulled from registry (matching docker-compose.yml):
#   - svitlo-power-api (back-end)
#   - svitlo-power-sse-api (sse-back-end)
#   - svitlo-power-grid-reporter (grid-reporter)
#   - svitlo-power-ui (front-end, nginx with baked-in dist)

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# --- Determine tag ---------------------------------------------------------
TAG="${1:-latest}"

# --- Check .env exists (used by docker-compose) ---------------------------
ENV_FILE="$REPO_ROOT/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo "Error: .env not found. Create it from .env.sample first."
    echo "Falling back to local build deploy.sh..."
    exec "$REPO_ROOT/deploy.sh" "$@"
fi

# --- Registry login --------------------------------------------------------
# Registry credentials can be in .env or provided via environment
if [ -z "${REGISTRY_URL:-}" ]; then
    # Try to load from .env
    if grep -q '^REGISTRY_URL=' "$ENV_FILE"; then
        set -a
        # shellcheck source=/dev/null
        source "$ENV_FILE"
        set +a
    fi
fi

if [ -z "${REGISTRY_URL:-}" ] || [ -z "${REGISTRY_USERNAME:-}" ] || [ -z "${REGISTRY_PASSWORD:-}" ]; then
    echo "Error: REGISTRY_URL, REGISTRY_USERNAME, or REGISTRY_PASSWORD not set."
    echo "Add them to .env or export them in environment."
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
# Pull all 4 custom images from registry with the specified tag
echo "Pulling images with tag: $TAG"

IMAGES=(
    "svitlo-power-api"
    "svitlo-power-sse-api"
    "svitlo-power-grid-reporter"
    "svitlo-power-ui"
)

for IMAGE in "${IMAGES[@]}"; do
    FULL_IMAGE="$REGISTRY_URL/$IMAGE:$TAG"
    echo "Pulling $FULL_IMAGE..."
    if ! docker pull "$FULL_IMAGE"; then
        echo "Error: Failed to pull $FULL_IMAGE from $REGISTRY_URL."
        echo "Falling back to local build deploy.sh..."
        exec "$REPO_ROOT/deploy.sh" "$@"
    fi

    # Retag to local name expected by docker-compose
    docker tag "$FULL_IMAGE" "$IMAGE:$TAG"
done

# Also pull base images used in docker-compose (redis)
echo "Pulling base images..."
docker pull redis:7 || true

# --- Stop existing containers ---------------------------------------------
echo "Stopping existing containers..."
docker compose down || { echo "Failed to stop containers"; exit 1; }

# --- Start containers with pulled images ----------------------------------
echo "Starting containers with registry images (tag: $TAG)..."
# Export TAG so docker-compose can use it if needed
export TAG
docker compose up -d || { echo "Failed to start containers"; exit 1; }

echo "Deployment successful!"

# --- Cleanup ---------------------------------------------------------------
echo "Cleaning up unused Docker resources..."
docker container prune -f
docker image prune -a -f
echo "Cleanup complete."