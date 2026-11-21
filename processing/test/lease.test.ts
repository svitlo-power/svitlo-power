import assert from "node:assert/strict";
import { test } from "node:test";
import { ProcessingLease } from "../src/lease/processing-lease.service.js";

interface FakeRedis {
  store: Map<string, string>;
  setCalls: unknown[];
  evalCalls: unknown[][];
  set(...args: unknown[]): Promise<string | null>;
  eval(...args: unknown[]): Promise<number>;
}

function fakeRedis(): FakeRedis {
  const store = new Map<string, string>();
  const setCalls: unknown[] = [];
  const evalCalls: unknown[][] = [];
  return {
    store,
    setCalls,
    evalCalls,
    async set(key: string, value: string, options?: { NX?: boolean }) {
      setCalls.push([key, value, options]);
      if (options?.NX && store.has(key)) return null;
      store.set(key, value);
      return "OK";
    },
    async eval(
      script: string,
      options: { keys: string[]; arguments: string[] },
    ) {
      evalCalls.push([script, options]);
      const [key] = options.keys;
      const [token, ttl] = options.arguments;
      if (script.includes("EXPIRE")) {
        if (store.get(key) !== token) return 0;
        store.set(key, token);
        return ttl ? 1 : 1;
      }
      if (store.get(key) !== token) return 0;
      store.delete(key);
      return 1;
    },
  };
}

test("a free lease is acquired and then renewed by its holder", async () => {
  const redis = fakeRedis();
  const lease = new ProcessingLease(redis as never, {
    key: "shadow:lock:processing:dashboard:v1",
    instanceId: "processing-1",
  });

  assert.equal(await lease.acquire(), true);
  assert.equal(lease.isHolder, true);
  assert.equal(
    redis.store.get("shadow:lock:processing:dashboard:v1"),
    "processing-1",
  );

  assert.equal(await lease.renew(), true);
  assert.equal(lease.isHolder, true);
});

test("a lease held by another instance is not acquired", async () => {
  const redis = fakeRedis();
  redis.store.set("shadow:lock:processing:dashboard:v1", "processing-other");

  const lease = new ProcessingLease(redis as never, {
    key: "shadow:lock:processing:dashboard:v1",
    instanceId: "processing-1",
  });

  assert.equal(await lease.acquire(), false);
  assert.equal(lease.isHolder, false);
});

test("losing the lease clears local state and notifies the caller", async () => {
  const redis = fakeRedis();
  let losses = 0;
  const lease = new ProcessingLease(redis as never, {
    key: "shadow:lock:processing:dashboard:v1",
    instanceId: "processing-1",
    onLost: () => {
      losses += 1;
    },
  });

  await lease.acquire();
  // Another instance steals the lease.
  redis.store.set("shadow:lock:processing:dashboard:v1", "processing-other");

  assert.equal(await lease.renew(), false);
  assert.equal(lease.isHolder, false);
  assert.equal(losses, 1);
});

test("releasing a lease only deletes it for the holder", async () => {
  const redis = fakeRedis();
  const lease = new ProcessingLease(redis as never, {
    key: "shadow:lock:processing:dashboard:v1",
    instanceId: "processing-1",
  });
  await lease.acquire();
  await lease.release();

  assert.equal(lease.isHolder, false);
  assert.equal(redis.store.has("shadow:lock:processing:dashboard:v1"), false);
});
