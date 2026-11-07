import { createHash } from "node:crypto";
import { ThrottlerStorage } from "@nestjs/throttler";
import { RedisClientType } from "redis";

interface ThrottlerStorageRecord {
  totalHits: number;
  timeToExpire: number;
  isBlocked: boolean;
  timeToBlockExpire: number;
}

const incrementScript = `
local blockedFor = redis.call('PTTL', KEYS[2])
local currentHits = tonumber(redis.call('GET', KEYS[1]) or '0')
if blockedFor > 0 then
  return { currentHits, redis.call('PTTL', KEYS[1]), 1, blockedFor }
end

local hits = redis.call('INCR', KEYS[1])
local windowFor = redis.call('PTTL', KEYS[1])
if hits == 1 or windowFor < 0 then
  redis.call('PEXPIRE', KEYS[1], ARGV[1])
  windowFor = tonumber(ARGV[1])
end

local blocked = 0
local blockFor = 0
if hits > tonumber(ARGV[2]) then
  local blockDuration = tonumber(ARGV[3])
  if blockDuration > 0 then
    redis.call('SET', KEYS[2], '1', 'PX', blockDuration)
    blocked = 1
    blockFor = blockDuration
  else
    blocked = 1
    blockFor = windowFor
  end
end

return { hits, windowFor, blocked, blockFor }
`;

export class RedisThrottlerStorage implements ThrottlerStorage {
  constructor(private readonly redis: RedisClientType) {}

  async increment(
    key: string,
    ttl: number,
    limit: number,
    blockDuration: number,
    throttlerName: string,
  ): Promise<ThrottlerStorageRecord> {
    const digest = createHash("sha256")
      .update(`${throttlerName}:${key}`)
      .digest("hex");
    const keyPrefix = `app-backend:rate-limit:{${digest}}`;
    const result = (await this.redis.eval(incrementScript, {
      keys: [`${keyPrefix}:hits`, `${keyPrefix}:blocked`],
      arguments: [String(ttl), String(limit), String(blockDuration)],
    })) as number[];
    const [totalHits, windowRemaining, isBlocked, blockRemaining] =
      result.map(Number);

    return {
      totalHits,
      timeToExpire: Math.max(0, Math.ceil(windowRemaining / 1000)),
      isBlocked: isBlocked === 1,
      timeToBlockExpire: Math.max(0, Math.ceil(blockRemaining / 1000)),
    };
  }
}
