# Redis Conventions for Dashboard Snapshots

## Key Naming

| Purpose | Pattern | Example |
|---------|---------|---------|
| Snapshot (global) | `cache:dashboard:v1:global` | `cache:dashboard:v1:global` |
| Invalidation channel | `cache:dashboard:v1:invalidations` | `cache:dashboard:v1:invalidations` |
| Processing lease | `lock:processing:dashboard:v1` | `lock:processing:dashboard:v1` |
| Epoch counter | `meta:dashboard:epoch` | `meta:dashboard:epoch` |
| Version counter | `meta:dashboard:version` | `meta:dashboard:version` |

> **No tenant scope** — this system has a single global snapshot.

## Snapshot Key

- **Value**: JSON string matching `dashboard-snapshot/v1.json` schema (includes `epoch`, `version`, `generatedAt`, `buildings`, `config`, `outagesSchedules`)
- **TTL**: 86400 seconds (24 hours) — disposable cache, not durable
- **Atomic write**: Single Lua script with **lease fencing** and **compare-and-set on (epoch, version)**
- **Version source**: `(epoch, version)` tuple from Redis counters `meta:dashboard:epoch` and `meta:dashboard:version`

## Invalidation Notification

Published to `cache:dashboard:v1:invalidations` after successful snapshot write.

```json
{
  "key": "cache:dashboard:v1:global",
  "epoch": 1,
  "version": 42,
  "generatedAt": "2026-10-27T18:00:00.000Z"
}
```

Fields:
- `key` — Redis key that was updated (consumers can read directly)
- `epoch` — Generation epoch (increments on Redis flush/failover)
- `version` — Snapshot version within epoch (monotonic integer)
- `generatedAt` — ISO 8601 timestamp from snapshot

## Refresh Request (HTTP, not Pub/Sub)

**The ADR rejects request/reply over Pub/Sub.** BFFs call an HTTP endpoint on the current producer:

- **Phase 1–3**: `POST http://back-end/internal/v1/snapshots/refresh`
- **Phase 5+**: `POST http://processor/internal/v1/snapshots/refresh`

Request body:
```json
{ "reason": "cache-miss", "requestedBy": "app-back-end-3" }
```

Response: `{ "accepted": true, "epoch": 1, "version": 43 }` (or current snapshot if already fresh)

Producer coalesces concurrent requests server-side (500ms window).

## Atomic Write Lua Script (with Lease Fencing & CAS)

```lua
-- KEYS[1] = snapshot key (cache:dashboard:v1:global)
-- KEYS[2] = invalidation channel (cache:dashboard:v1:invalidations)
-- KEYS[3] = lease key (lock:processing:dashboard:v1)
-- KEYS[4] = epoch key (meta:dashboard:epoch)
-- KEYS[5] = version key (meta:dashboard:version)
-- ARGV[1] = snapshot JSON string (must contain epoch, version, generatedAt)
-- ARGV[2] = notification JSON string
-- ARGV[3] = TTL in seconds (86400)
-- ARGV[4] = lease token (instance ID)
-- ARGV[5] = expected epoch (from snapshot JSON)
-- ARGV[6] = expected version (from snapshot JSON)

local snapshot_json = ARGV[1]
local notification_json = ARGV[2]
local ttl = tonumber(ARGV[3])
local lease_token = ARGV[4]
local expected_epoch = tonumber(ARGV[5])
local expected_version = tonumber(ARGV[6])

-- 1. Verify lease holder (fencing)
local current_lease = redis.call('GET', KEYS[3])
if current_lease ~= lease_token then
  return {0, 'lease-lost', 'not-lease-holder'}
end

-- 2. Compare-and-set on (epoch, version)
local current_epoch = tonumber(redis.call('GET', KEYS[4]) or '0')
local current_version = tonumber(redis.call('GET', KEYS[5]) or '0')

if expected_epoch < current_epoch then
  return {0, 'epoch-stale', 'expected-epoch ' .. expected_epoch .. ' < current ' .. current_epoch}
end
if expected_epoch == current_epoch and expected_version <= current_version then
  return {0, 'version-stale', 'expected-version ' .. expected_version .. ' <= current ' .. current_version}
end

-- 3. Write snapshot atomically
redis.call('SET', KEYS[1], snapshot_json, 'EX', ttl)

-- 4. Update counters
redis.call('SET', KEYS[4], expected_epoch)
redis.call('SET', KEYS[5], expected_version)

-- 5. Publish invalidation
redis.call('PUBLISH', KEYS[2], notification_json)

return {1, 'ok', 'epoch=' .. expected_epoch .. ',version=' .. expected_version}
```

Usage (Redis client):
```python
script = redis.register_script(LUA_SCRIPT)
script(
    keys=[snapshot_key, channel, lease_key, epoch_key, version_key],
    args=[snapshot_json, notification_json, 86400, lease_token, epoch, version]
)
```

## Consumer Behavior

### Initial Load
1. Subscribe to invalidation channel
2. `GET` snapshot key
3. If miss: call HTTP refresh endpoint, wait for notification (max 5s), then `GET` again
4. Store local copy with `(epoch, version)`

### On Notification
1. Parse `epoch`, `version` from notification
2. If `epoch > local_epoch` OR (`epoch == local_epoch` AND `version > local_version`):
   - `GET` snapshot key, update local copy
3. Emit SSE event with `event: dashboard-update`, `id: <epoch>-<version>`, `data: <snapshot>`

### Reconnect
1. Re-subscribe to invalidation channel
2. `GET` snapshot key
2. If `epoch > local_epoch` OR (`epoch == local_epoch` AND `version > local_version`): update local copy
3. Emit SSE event with full snapshot

### Periodic Reconciliation
Every 60 seconds: `GET` snapshot key, compare `(epoch, version)` with local. If stale, update.

### Epoch Change Handling
When `epoch > local_epoch`: consumer **must accept** the new snapshot even if `version` is lower (e.g., 1). This handles Redis flush/failover.

## Processing Service Lease

Single-writer enforcement for snapshot generation.

- **Key**: `lock:processing:dashboard:v1`
- **Value**: Processing instance ID (e.g., `processor-3`)
- **TTL**: 30 seconds (renewed every 10s)
- **Acquisition**: `SET lock:processing:dashboard:v1 <instance-id> NX EX 30`
- **Renewal**: Lua script — only renew if value matches instance ID
- **Release**: Lua script — only delete if value matches instance ID

```lua
-- Renewal
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('EXPIRE', KEYS[1], 30)
else
  return 0
end

-- Release
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
else
  return 0
end
```

## Monitoring Keys

| Metric | Key Pattern | Alert Threshold |
|--------|-------------|-----------------|
| Snapshot age | `cache:dashboard:v1:global` (now - generatedAt) | > 300s (5 min) |
| Version lag | Consumer local (epoch,version) vs Redis | > 1 version for > 60s |
| Missed notifications | Counter per consumer | > 0 in 5 min |
| Refresh latency | HTTP refresh request → notification | p99 > 10s |
| Lease holder changes | `lock:processing:dashboard:v1` | > 2/min (flapping) |
| Epoch changes | `meta:dashboard:epoch` | > 0 (unexpected) |

## Version Compatibility

- **v1**: Current schema. Additive optional fields only.
- **Breaking change**: New major version → `cache:dashboard:v2:*`, new channel `cache:dashboard:v2:invalidations`
- Consumers support **at most two versions** simultaneously during migration.
- Old version TTL expires naturally; no explicit deletion needed.

## Redis Persistence Note

Redis runs with `--appendonly yes` and a volume (`docker-compose.yml`). The "disposable cache" semantics mean:
- Application logic must handle cache miss by rebuilding from source
- Version/epoch counters survive restart but reset on `FLUSHALL` or volume loss
- Epoch mechanism handles counter reset gracefully