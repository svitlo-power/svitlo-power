import assert from "node:assert/strict";
import { test } from "node:test";
import { ShadowPublisher } from "../src/shadow/shadow-publisher.service.js";
import type { ProcessingLease } from "../src/lease/processing-lease.service.js";
import type { MetricsService } from "../src/metrics/metrics.service.js";
import type { DashboardSnapshot } from "../src/shared.js";

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
): ShadowPublisher {
  const lease = {
    get leaseToken() {
      return token;
    },
  } as unknown as ProcessingLease;
  const redis = {
    eval: async () => evalResult,
  };
  return new ShadowPublisher(
    redis as never,
    lease,
    { shadowModeEnabled: true } as never,
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
  const instance = new ShadowPublisher(
    redis as never,
    lease,
    { shadowModeEnabled: true } as never,
    metrics(),
  );

  const result = await instance.publish(snapshot());
  assert.equal(result.published, false);
  assert.equal(result.reason, "exception");
});
