export const PROCESSING = Symbol("PROCESSING");
export const REDIS_READER = Symbol("REDIS_READER");
export const REDIS_WRITER = Symbol("REDIS_WRITER");
/**
 * Dedicated client for the snapshot refresh subscription.
 *
 * A Redis client in subscriber mode can only run `SUBSCRIBE`/`UNSUBSCRIBE`, so
 * it cannot share the reader or writer connection.
 */
export const REDIS_SUBSCRIBER = Symbol("REDIS_SUBSCRIBER");
export const PROCESSING_LEASE = Symbol("PROCESSING_LEASE");
export const SNAPSHOT_BUILDER = Symbol("SNAPSHOT_BUILDER");
export const SHADOW_COMPARATOR = Symbol("SHADOW_COMPARATOR");
/**
 * The publisher the processing flow writes through.
 *
 * Exactly one is active, chosen from `FEATURE_PROCESSING_PUBLISH_ENABLED` by
 * the module factory — never from whether a provider was injected. Both
 * publishers satisfy {@link SnapshotPublisherLike}, so the service writes to
 * the shadow namespace before the cutover and to the production keys after it.
 */
export const ACTIVE_PUBLISHER = Symbol("ACTIVE_PUBLISHER");
