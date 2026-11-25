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
