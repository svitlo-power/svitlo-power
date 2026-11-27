/**
 * Atomic production snapshot write with lease fencing and compare-and-set on
 * (epoch, committed version).
 *
 * This is the script the legacy Python producer runs; Processing uses the same
 * one after the cutover so the on-wire contract and the fencing semantics are
 * identical on both sides of the rollback.
 *
 * KEYS[1] = snapshot key (cache:dashboard:v1:global)
 * KEYS[2] = invalidation channel (cache:dashboard:v1:invalidations)
 * KEYS[3] = lease key (lock:processing:dashboard:v1)
 * KEYS[4] = epoch key (meta:dashboard:epoch)
 * KEYS[5] = committed version key (meta:dashboard:version)
 * ARGV[1] = snapshot JSON string
 * ARGV[2] = notification JSON string
 * ARGV[3] = TTL in seconds
 * ARGV[4] = lease token
 * ARGV[5] = expected epoch
 * ARGV[6] = expected version
 */
export const LUA_WRITE_SCRIPT = `
local snapshot_json = ARGV[1]
local notification_json = ARGV[2]
local ttl = tonumber(ARGV[3])
local lease_token = ARGV[4]
local expected_epoch = tonumber(ARGV[5])
local expected_version = tonumber(ARGV[6])

local current_lease = redis.call('GET', KEYS[3])
if current_lease ~= lease_token then
  return {0, 'lease-lost', 'not-lease-holder'}
end

local current_epoch = tonumber(redis.call('GET', KEYS[4]) or '0')
local current_version = tonumber(redis.call('GET', KEYS[5]) or '0')

if expected_epoch < current_epoch then
  return {0, 'epoch-stale', 'expected-epoch ' .. expected_epoch .. ' < current ' .. current_epoch}
end
if expected_epoch == current_epoch and expected_version <= current_version then
  return {0, 'version-stale', 'expected-version ' .. expected_version .. ' <= current ' .. current_version}
end

redis.call('SET', KEYS[1], snapshot_json, 'EX', ttl)
redis.call('SET', KEYS[4], expected_epoch)
redis.call('SET', KEYS[5], expected_version)
redis.call('PUBLISH', KEYS[2], notification_json)

return {1, 'ok', 'epoch=' .. expected_epoch .. ',version=' .. expected_version}
`;

/**
 * Atomic shadow snapshot write with lease fencing and compare-and-set on
 * (epoch, committed version).
 *
 * Mirrors the legacy producer's Lua script, but every key it touches belongs to
 * the `shadow:` namespace, so a shadow write can never mutate production state.
 *
 * KEYS[1] = shadow snapshot key
 * KEYS[2] = shadow invalidation channel
 * KEYS[3] = shadow lease key
 * KEYS[4] = shadow epoch key
 * KEYS[5] = shadow committed version key
 * ARGV[1] = snapshot JSON string
 * ARGV[2] = notification JSON string
 * ARGV[3] = TTL in seconds
 * ARGV[4] = lease token
 * ARGV[5] = expected epoch
 * ARGV[6] = expected version
 */
export const LUA_SHADOW_WRITE_SCRIPT = `
local snapshot_json = ARGV[1]
local notification_json = ARGV[2]
local ttl = tonumber(ARGV[3])
local lease_token = ARGV[4]
local expected_epoch = tonumber(ARGV[5])
local expected_version = tonumber(ARGV[6])

local current_lease = redis.call('GET', KEYS[3])
if current_lease ~= lease_token then
  return {0, 'lease-lost', 'not-lease-holder'}
end

local current_epoch = tonumber(redis.call('GET', KEYS[4]) or '0')
local current_version = tonumber(redis.call('GET', KEYS[5]) or '0')

if expected_epoch < current_epoch then
  return {0, 'epoch-stale', 'expected-epoch ' .. expected_epoch .. ' < current ' .. current_epoch}
end
if expected_epoch == current_epoch and expected_version <= current_version then
  return {0, 'version-stale', 'expected-version ' .. expected_version .. ' <= current ' .. current_version}
end

redis.call('SET', KEYS[1], snapshot_json, 'EX', ttl)
redis.call('SET', KEYS[4], expected_epoch)
redis.call('SET', KEYS[5], expected_version)
redis.call('PUBLISH', KEYS[2], notification_json)

return {1, 'ok', 'epoch=' .. expected_epoch .. ',version=' .. expected_version}
`;

/** Renewal: only the current holder may extend the lease. */
export const LUA_LEASE_RENEW_SCRIPT = `
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('EXPIRE', KEYS[1], ARGV[2])
else
  return 0
end
`;

/** Release: only the current holder may delete the lease. */
export const LUA_LEASE_RELEASE_SCRIPT = `
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
`;

export interface ShadowWriteResult {
  success: boolean;
  reason: string;
  detail?: string;
}

export function parseShadowWriteResult(result: unknown): ShadowWriteResult {
  if (!Array.isArray(result)) {
    return { success: false, reason: "malformed-result" };
  }
  const [flag, reason, detail] = result as unknown[];
  return {
    success: Number(flag) === 1,
    reason: typeof reason === "string" ? reason : "unknown",
    detail: typeof detail === "string" ? detail : undefined,
  };
}
