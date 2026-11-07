import assert from "node:assert/strict";
import { test } from "node:test";
import { RedisClientType } from "redis";
import { RedisThrottlerStorage } from "../src/infrastructure/redis/redis-throttler.storage.js";

test("Redis throttler storage converts Redis millisecond expirations to Nest seconds", async () => {
  let observedKeys: string[] = [];
  let observedArguments: string[] = [];
  const redis = {
    eval: async (
      _script: string,
      options: { keys: string[]; arguments: string[] },
    ) => {
      observedKeys = options.keys;
      observedArguments = options.arguments;
      return [9, 1_234, 1, 59_001];
    },
  } as unknown as RedisClientType;

  const result = await new RedisThrottlerStorage(redis).increment(
    "mobile-ip:push-route",
    60_000,
    8,
    300_000,
    "default",
  );

  assert.deepEqual(result, {
    totalHits: 9,
    timeToExpire: 2,
    isBlocked: true,
    timeToBlockExpire: 60,
  });
  assert.equal(observedArguments.join(","), "60000,8,300000");
  assert.equal(observedKeys.length, 2);
  assert.ok(
    observedKeys.every((key) => key.startsWith("app-backend:rate-limit:{")),
  );
  assert.ok(observedKeys.every((key) => !key.includes("mobile-ip")));
});
