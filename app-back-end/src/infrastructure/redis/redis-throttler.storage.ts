import { createHash } from "node:crypto";
import { Logger } from "@nestjs/common";
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

const FAILURE_LOG_INTERVAL_MS = 30_000;

/**
 * Rate limiting is a safeguard, not a dependency: when Redis is unavailable the
 * storage fails open so mobile requests that do not need Redis keep working.
 */
export class RedisThrottlerStorage implements ThrottlerStorage {
  private readonly logger = new Logger(RedisThrottlerStorage.name);
  private lastFailureLogAt = 0;

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
    let result: number[];
    try {
      result = (await this.redis.eval(incrementScript, {
        keys: [`${keyPrefix}:hits`, `${keyPrefix}:blocked`],
        arguments: [String(ttl), String(limit), String(blockDuration)],
      })) as number[];
    } catch (error) {
      this.logFailure(error);
      return {
        totalHits: 0,
        timeToExpire: 0,
        isBlocked: false,
        timeToBlockExpire: 0,
      };
    }
    const [totalHits, windowRemaining, isBlocked, blockRemaining] =
      result.map(Number);

    return {
      totalHits,
      timeToExpire: Math.max(0, Math.ceil(windowRemaining / 1000)),
      isBlocked: isBlocked === 1,
      timeToBlockExpire: Math.max(0, Math.ceil(blockRemaining / 1000)),
    };
  }

  private logFailure(error: unknown): void {
    const now = Date.now();
    if (now - this.lastFailureLogAt < FAILURE_LOG_INTERVAL_MS) return;
    this.lastFailureLogAt = now;
    this.logger.warn(
      `Rate limiting disabled while Redis is unavailable: ${error instanceof Error ? error.name : "unknown error"}`,
    );
  }
}
