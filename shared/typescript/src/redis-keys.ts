/**
 * Redis key and channel names for the dashboard snapshot contract.
 *
 * The production names are owned by the legacy Python producer and must not be
 * written by Processing while shadow mode is active. Shadow names are derived
 * from them by prefixing `shadow:` so the two namespaces can never collide.
 */

export const SNAPSHOT_KEY = "cache:dashboard:v1:global";
export const INVALIDATION_CHANNEL = "cache:dashboard:v1:invalidations";
export const LEASE_KEY = "lock:processing:dashboard:v1";
export const EPOCH_KEY = "meta:dashboard:epoch";
export const VERSION_NEXT_KEY = "meta:dashboard:version:next";
export const VERSION_COMMITTED_KEY = "meta:dashboard:version";

export const SHADOW_PREFIX = "shadow:";

export const SHADOW_SNAPSHOT_KEY = `${SHADOW_PREFIX}${SNAPSHOT_KEY}`;
export const SHADOW_INVALIDATION_CHANNEL = `${SHADOW_PREFIX}${INVALIDATION_CHANNEL}`;
export const SHADOW_LEASE_KEY = `${SHADOW_PREFIX}${LEASE_KEY}`;
export const SHADOW_EPOCH_KEY = `${SHADOW_PREFIX}${EPOCH_KEY}`;
export const SHADOW_VERSION_NEXT_KEY = `${SHADOW_PREFIX}${VERSION_NEXT_KEY}`;
export const SHADOW_VERSION_COMMITTED_KEY = `${SHADOW_PREFIX}${VERSION_COMMITTED_KEY}`;

export const LEASE_TTL_SECONDS = 30;
export const LEASE_RENEW_INTERVAL_SECONDS = 10;
export const SNAPSHOT_TTL_SECONDS = 86_400;

/** Every key the shadow flow is allowed to touch. */
export const SHADOW_KEYS = [
  SHADOW_SNAPSHOT_KEY,
  SHADOW_INVALIDATION_CHANNEL,
  SHADOW_LEASE_KEY,
  SHADOW_EPOCH_KEY,
  SHADOW_VERSION_NEXT_KEY,
  SHADOW_VERSION_COMMITTED_KEY,
] as const;

/** Production keys the shadow flow may read but never write. */
export const PRODUCTION_READ_KEYS = [SNAPSHOT_KEY] as const;

export function isShadowKey(key: string): boolean {
  return key.startsWith(SHADOW_PREFIX);
}
