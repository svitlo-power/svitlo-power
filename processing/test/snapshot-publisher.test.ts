import assert from "node:assert/strict";
import { test } from "node:test";
import { SnapshotPublisher } from "../src/snapshot/snapshot-publisher.service.js";
import type { ProcessingLease } from "../src/lease/processing-lease.service.js";
import type { MetricsService } from "../src/metrics/metrics.service.js";
import {
  EPOCH_KEY,
  INVALIDATION_CHANNEL,
  LEASE_KEY,
  SNAPSHOT_KEY,
  VERSION_COMMITTED_KEY,
  VERSION_NEXT_KEY,
  type DashboardSnapshot,
} from "../src/shared.js";

function snapshot(): DashboardSnapshot {
  return {
    epoch: 1_700_000_000_000,
    version: 3,
    generatedAt: new Date().toISOString(),
    buildings: [],
    config: { title: { en: "Dashboard" }, outagesSchedule: null },
    outagesSchedules: {},
  };
}

function metrics(): MetricsService {
  const noop = () => undefined;
  return {
    writeError: noop,
    observePublishDuration: noop,
    setSnapshotState: noop,
  } as unknown as MetricsService;
}

function publisher(
  evalResult: unknown,
  token: string | null = "processing-1",
): SnapshotPublisher {
  const lease = {
    get leaseToken() {
      return token;
    },
  } as unknown as ProcessingLease;
  const redis = {
    eval: async () => evalResult,
  };
  return new SnapshotPublisher(
    redis as never,
    lease,
    { publishEnabled: true } as never,
    metrics(),
  );
}

test("a successful Lua result publishes the snapshot", async () => {
  const result = await publisher([1, "ok", "epoch=1,version=3"]).publish(
    snapshot(),
  );
  assert.equal(result.published, true);
  assert.equal(result.reason, "ok");
});

test("the write targets the production keys and the invalidation channel", async () => {
  const lease = {
    get leaseToken() {
      return "processing-1";
    },
  } as unknown as ProcessingLease;
  let observedKeys: string[] = [];
  let observedArguments: string[] = [];
  const redis = {
    eval: async (_script: string, options: unknown) => {
      const call = options as { keys: string[]; arguments: string[] };
      observedKeys = call.keys;
      observedArguments = call.arguments;
      return [1, "ok", ""];
    },
  };
  const instance = new SnapshotPublisher(
    redis as never,
    lease,
    { publishEnabled: true } as never,
    metrics(),
  );

  await instance.publish(snapshot());

  // A shadow key here would leave the BFFs reading a snapshot nobody updates.
  assert.deepEqual(observedKeys, [
    SNAPSHOT_KEY,
    INVALIDATION_CHANNEL,
    LEASE_KEY,
    EPOCH_KEY,
    VERSION_COMMITTED_KEY,
  ]);
  assert.equal(observedArguments[3], "processing-1");
});

test("a lease fence rejection is reported instead of throwing", async () => {
  const result = await publisher([0, "lease-lost", "not-lease-holder"]).publish(
    snapshot(),
  );
  assert.equal(result.published, false);
  assert.equal(result.reason, "lease-lost");
});

test("a stale epoch or version is reported", async () => {
  const staleEpoch = await publisher([0, "epoch-stale", "5 < 6"]).publish(
    snapshot(),
  );
  assert.equal(staleEpoch.reason, "epoch-stale");

  const staleVersion = await publisher([0, "version-stale", "3 <= 3"]).publish(
    snapshot(),
  );
  assert.equal(staleVersion.reason, "version-stale");
});

test("a malformed Lua result is reported as such", async () => {
  const result = await publisher("not-an-array").publish(snapshot());
  assert.equal(result.published, false);
  assert.equal(result.reason, "malformed-result");
});

test("publishing without a lease is rejected before touching Redis", async () => {
  const result = await publisher([1, "ok", ""], null).publish(snapshot());
  assert.equal(result.published, false);
  assert.equal(result.reason, "no-lease");
});

test("a Redis failure is reported as an exception", async () => {
  const lease = {
    get leaseToken() {
      return "processing-1";
    },
  } as unknown as ProcessingLease;
  const redis = {
    eval: async () => {
      throw new Error("connection closed");
    },
  };
  const instance = new SnapshotPublisher(
    redis as never,
    lease,
    { publishEnabled: true } as never,
    metrics(),
  );

  const result = await instance.publish(snapshot());
  assert.equal(result.published, false);
  assert.equal(result.reason, "exception");
});

interface FakeRedis {
  store: Map<string, string>;
  incr(key: string): Promise<number>;
  get(key: string): Promise<string | null>;
  set(key: string, value: string): Promise<string>;
}

function fakeRedis(initial: Record<string, string> = {}): FakeRedis {
  const store = new Map<string, string>(Object.entries(initial));
  return {
    store,
    async incr(key: string) {
      const next = Number.parseInt(store.get(key) ?? "0", 10) + 1;
      store.set(key, String(next));
      return next;
    },
    async get(key: string) {
      return store.get(key) ?? null;
    },
    async set(key: string, value: string) {
      store.set(key, value);
      return "OK";
    },
  };
}

function publisherWith(redis: FakeRedis): SnapshotPublisher {
  const lease = {
    get leaseToken() {
      return "processing-1";
    },
  } as unknown as ProcessingLease;
  return new SnapshotPublisher(
    redis as never,
    lease,
    { publishEnabled: true } as never,
    metrics(),
  );
}

test("version keys are seeded only when absent", async () => {
  const redis = fakeRedis();
  const instance = publisherWith(redis);

  const epoch = await instance.initialiseVersionKeys(1_700_000_000_000);

  assert.equal(epoch, 1_700_000_000_000);
  assert.equal(redis.store.get(EPOCH_KEY), "1700000000000");
  assert.equal(redis.store.get(VERSION_NEXT_KEY), "1");
  assert.equal(redis.store.get(VERSION_COMMITTED_KEY), "0");
  assert.equal(await instance.nextVersion(), 2);
});

test("the epoch never rewinds across a restart or a Redis flush", async () => {
  const redis = fakeRedis({
    [EPOCH_KEY]: "1_800_000_000_000".replace("_", ""),
    [SNAPSHOT_KEY]: JSON.stringify({ epoch: 1_900_000_000_000 }),
  });
  const instance = publisherWith(redis);

  const epoch = await instance.initialiseVersionKeys(1_700_000_000_000);

  // A snapshot written by the legacy producer before the rollback carries the
  // newer epoch; seeding from the process start time would make every
  // subsequent write `epoch-stale`.
  assert.equal(epoch, 1_900_000_000_000);
});

test("an existing version allocator is not reset", async () => {
  const redis = fakeRedis({ [VERSION_NEXT_KEY]: "41" });
  const instance = publisherWith(redis);

  await instance.initialiseVersionKeys(1_700_000_000_000);

  assert.equal(await instance.nextVersion(), 42);
});
