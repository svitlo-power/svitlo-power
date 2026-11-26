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

/**
 * "Data changed" notification channel for the Phase 5 cutover.
 *
 * The legacy back-end publishes a hint here after every mutation that used to
 * call `refresh_and_publish()` inline; Processing subscribes and rebuilds. The
 * channel is deliberately separate from `INVALIDATION_CHANNEL`, which is the
 * BFF-facing read path and must keep its current meaning.
 *
 * The name is versioned so a future contract change can be rolled out beside
 * the current one instead of breaking a live subscription.
 */
export const SNAPSHOT_REFRESH_CHANNEL = "processing:triggers:snapshot-refresh";

/** Payload of a `SNAPSHOT_REFRESH_CHANNEL` notification. */
export interface SnapshotRefreshNotification {
  /** Why the data changed; used as a metric label and log field. */
  reason: string;
  /**
   * Optional snapshot sections the publisher believes changed.
   *
   * Reserved: no caller sets it and Processing ignores it. Kept in the contract
   * so a future consumer can use it without a payload change.
   */
  changedSections?: string[];
  /** Process that published the notification, for example `back-end`. */
  source: string;
}

/** Recognised `reason` values, kept in sync with the legacy publisher. */
export const SNAPSHOT_REFRESH_REASONS = [
  "config-change",
  "buildings-change",
  "station-change",
  "outages-change",
] as const;

export type SnapshotRefreshReason = (typeof SNAPSHOT_REFRESH_REASONS)[number];

/**
 * Parses a raw pub/sub payload.
 *
 * Returns `null` for anything that is not a usable hint: Processing must never
 * treat the payload as state, so an unparseable message is dropped rather than
 * guessed at.
 */
export function parseSnapshotRefreshNotification(
  raw: string,
): SnapshotRefreshNotification | null {
  let payload: unknown;
  try {
    payload = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof payload !== "object" || payload === null) return null;
  const candidate = payload as Record<string, unknown>;
  const { reason, source } = candidate;
  if (typeof reason !== "string" || reason.length === 0) return null;
  if (typeof source !== "string" || source.length === 0) return null;
  // `reason` becomes a metric label, so an unknown value would create an
  // unbounded series for anything that can PUBLISH to the channel. Fold it into
  // a fixed `other` bucket instead.
  const normalisedReason = (
    SNAPSHOT_REFRESH_REASONS as readonly string[]
  ).includes(reason)
    ? reason
    : "other";
  const changedSections = Array.isArray(candidate.changedSections)
    ? candidate.changedSections.filter(
        (section): section is string => typeof section === "string",
      )
    : undefined;
  return { reason: normalisedReason, source, changedSections };
}

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
