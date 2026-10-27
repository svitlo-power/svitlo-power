# Redis Conventions for Dashboard Snapshots

## Key Naming

| Purpose | Pattern | Example |
|---------|---------|---------|
| Snapshot (global) | `cache:dashboard:v1:global` | `cache:dashboard:v1:global` |
| Snapshot (tenant) | `cache:dashboard:v1:tenant:{tenantId}` | `cache:dashboard:v1:tenant:acme-corp` |
| Invalidation channel | `cache:dashboard:v1:invalidations` | `cache:dashboard:v1:invalidations` |
| Refresh request channel | `cache:dashboard:v1:refresh-requests` | `cache:dashboard:v1:refresh-requests` |
| Processing lease | `lock:processing:dashboard:v1` | `lock:processing:dashboard:v1` |

## Snapshot Key

- **Value**: JSON string matching `dashboard-snapshot/v1.json` schema
- **TTL**: 86400 seconds (24 hours) — disposable cache, not durable
- **Atomic write**: Single Lua script (see below)
- **Version source**: Monotonic integer from Processing service (stored in snapshot `version` field)

## Invalidation Notification

Published to `cache:dashboard:v1:invalidations` after successful snapshot write.

```json
{
  "key": "cache:dashboard:v1:global",
  "version": 42,
  "scope": "global",
  "generatedAt": "2026-10-27T18:00:00.000Z"
}
```

Fields:
- `key` — Redis key that was updated (consumers can read directly)
- `version` — Snapshot version (monotonic integer)
- `scope` — `global` or `tenant:{tenantId}`
- `generatedAt` — ISO 8601 timestamp from snapshot

## Refresh Request

BFFs publish to `cache:dashboard:v1:refresh-requests` on cache miss or explicit refresh need.

```json
{
  "scope": "global",
  "requestedBy": "app-back-end-3",
  "requestedAt": "2026-10-27T18:05:12.000Z",
  "reason": "cache-miss"
}
```

Processing subscribes, coalesces requests within 500ms window, triggers one refresh.

## Atomic Write Lua Script

```lua
-- KEYS[1] = snapshot key (e.g., cache:dashboard:v1:global)
-- KEYS[2] = invalidation channel
-- ARGV[1] = snapshot JSON string
-- ARGV[2] = notification JSON string
-- ARGV[3] = TTL in seconds (86400)

local snapshot = ARGV[1]
local notification = ARGV[2]
local ttl = tonumber(ARGV[3])

-- Write snapshot
redis.call('SET', KEYS[1], snapshot, 'EX', ttl)

-- Publish invalidation
redis.call('PUBLISH', KEYS[2], notification)

return {1, 'ok'}
```

Usage (Redis client):
```python
script = redis.register_script(LUA_SCRIPT)
script(keys=[snapshot_key, channel], args=[snapshot_json, notification_json, 86400])
```

## Consumer Behavior

### Initial Load
1. Subscribe to invalidation channel
2. `GET` snapshot key
3. If miss: publish refresh request, wait for notification (max 5s), then `GET` again
4. Store local copy with `version`

### On Notification
1. Parse `version` from notification
2. If `version > local_version`: `GET` snapshot key, update local copy
3. Emit SSE event with `event: dashboard-update`, `id: <version>`, `data: <snapshot>`

### Reconnect
1. Re-subscribe to invalidation channel
2. `GET` snapshot key
3. If `version > local_version`: update local copy
4. Emit SSE event with full snapshot

### Periodic Reconciliation
Every 60 seconds: `GET` snapshot key, compare `version` with local. If stale, update.

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
| Snapshot age | `cache:dashboard:v1:*` (TTL remaining) | < 300s (5 min) |
| Version lag | Consumer local version vs Redis version | > 1 for > 30s |
| Missed notifications | Counter per consumer | > 0 in 5 min |
| Refresh latency | Refresh request → notification | p99 > 10s |
| Lease holder changes | `lock:processing:dashboard:v1` | > 2/min (flapping) |

## Version Compatibility

- **v1**: Current schema. Additive optional fields only.
- **Breaking change**: New major version → `cache:dashboard:v2:*`, new channel `cache:dashboard:v2:invalidations`
- Consumers support **at most two versions** simultaneously during migration.
- Old version TTL expires naturally; no explicit deletion needed.