import assert from "node:assert/strict";
import { test } from "node:test";
import { ProcessingService } from "../src/processing/processing.service.js";
import type { ProcessingLease } from "../src/lease/processing-lease.service.js";
import type { SnapshotBuilder } from "../src/snapshot/snapshot.builder.js";
import type { SnapshotValidator } from "../src/snapshot/snapshot.validator.js";
import type { ShadowPublisher } from "../src/shadow/shadow-publisher.service.js";
import type { ShadowComparator } from "../src/shadow/shadow-comparator.service.js";
import type { MetricsService } from "../src/metrics/metrics.service.js";
import type { DashboardSnapshot } from "../src/shared.js";

const EPOCH = 1_700_000_000_000;

function snapshot(version: number): DashboardSnapshot {
  return {
    epoch: EPOCH,
    version,
    generatedAt: new Date().toISOString(),
    buildings: [],
    config: { title: { en: "Dashboard" }, outagesSchedule: null },
    outagesSchedules: {},
  };
}

function metrics(): MetricsService {
  const noop = () => undefined;
  return {
    refreshRequest: noop,
    refreshCoalescedCount: noop,
    observeBuildDuration: noop,
    writeError: noop,
    setSnapshotState: noop,
  } as unknown as MetricsService;
}

interface HarnessOptions {
  holder?: boolean;
  publishReason?: string;
  buildError?: Error;
}

function harness(options: HarnessOptions = {}) {
  const state = {
    epoch: 0,
    holder: options.holder ?? true,
    listeners: [] as Array<() => void>,
  };

  const lease = {
    get isHolder() {
      return state.holder;
    },
    get leaseToken() {
      return state.holder ? "processing-1" : null;
    },
    acquire: async () => state.holder,
    start: () => undefined,
    release: async () => undefined,
    onAcquired: (listener: () => void) => {
      state.listeners.push(listener);
    },
  } as unknown as ProcessingLease;

  const builder = {
    build: async () => {
      if (options.buildError) throw options.buildError;
      return {
        snapshot: snapshot(1),
        timing: { startedAt: 0, finishedAt: 1, durationSeconds: 0.001 },
      };
    },
  } as unknown as SnapshotBuilder;

  const validator = {
    validate: () => ({ valid: true, errors: [] }),
  } as unknown as SnapshotValidator;

  const publisher = {
    initialiseVersionKeys: async () => EPOCH,
    nextVersion: async () => 1,
    publish: async () => ({
      published: options.publishReason === undefined,
      reason: options.publishReason ?? "ok",
    }),
  } as unknown as ShadowPublisher;

  const comparator = {
    compareWithProduction: async () => ({
      compared: false,
      matches: false,
      parity: 0,
      comparedFields: 0,
      mismatches: 0,
      reason: "no-baseline",
    }),
  } as unknown as ShadowComparator;

  const service = new ProcessingService(
    { shadowModeEnabled: true } as never,
    lease,
    builder,
    validator,
    publisher,
    comparator,
    metrics(),
  );

  // `reconcile` swallows nothing: a failing build rejects, and the startup path
  // is what records the failure for health reporting.
  return { service, state };
}

test("a replica without the lease reports no-lease and stays healthy", async () => {
  const { service } = harness({ holder: false });

  const result = await service.reconcile("scheduled");

  assert.equal(result.built, false);
  assert.equal(result.reason, "no-lease");
  // Standby replicas must not fail readiness, or multi-replica deploys flap.
  assert.equal(service.status(), "healthy");
  assert.equal(service.details().lease_held, false);
});

test("re-acquiring the lease resets the cached epoch", async () => {
  const { service, state } = harness();
  await service.reconcile("startup");
  assert.equal(service.details().epoch, EPOCH);

  state.listeners.forEach((listener) => listener());
  assert.equal(service.details().epoch, 0);
});

test("a failed build is reflected in the reported status", async () => {
  const { service } = harness({ buildError: new Error("mongo down") });

  // The startup path catches the failure and records it for health reporting.
  await service.onApplicationBootstrap();
  assert.equal(service.status(), "unhealthy");
  assert.equal(service.details().last_build_at, null);
});

test("last_build_at reports the build time, not the request time", async () => {
  const { service } = harness();
  const before = Date.now();
  await service.reconcile("scheduled");
  const details = service.details();

  assert.ok(details.last_build_at !== null);
  const built = Date.parse(details.last_build_at as string);
  assert.ok(built >= before && built <= Date.now());
});

test("a request arriving mid-build awaits the follow-up build", async () => {
  let release: (() => void) | undefined;
  let builds = 0;
  const state = { holder: true, listeners: [] as Array<() => void> };
  const lease = {
    get isHolder() {
      return state.holder;
    },
    get leaseToken() {
      return "processing-1";
    },
    acquire: async () => true,
    start: () => undefined,
    release: async () => undefined,
    onAcquired: (listener: () => void) => {
      state.listeners.push(listener);
    },
  } as unknown as ProcessingLease;

  const builder = {
    build: async () => {
      builds += 1;
      if (builds === 1) {
        // Hold the first build open so the second request arrives mid-build.
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      }
      return {
        snapshot: snapshot(builds),
        timing: { startedAt: 0, finishedAt: 1, durationSeconds: 0.001 },
      };
    },
  } as unknown as SnapshotBuilder;

  const service = new ProcessingService(
    { shadowModeEnabled: true } as never,
    lease,
    builder,
    {
      validate: () => ({ valid: true, errors: [] }),
    } as unknown as SnapshotValidator,
    {
      initialiseVersionKeys: async () => EPOCH,
      nextVersion: async () => builds,
      publish: async () => ({ published: true, reason: "ok" }),
    } as unknown as ShadowPublisher,
    {
      compareWithProduction: async () => ({
        compared: false,
        matches: false,
        parity: 0,
        comparedFields: 0,
        mismatches: 0,
        reason: "no-baseline",
      }),
    } as unknown as ShadowComparator,
    metrics(),
  );

  const leader = service.reconcile("config-change");
  // Let the leader reach its first await inside the builder.
  await new Promise((resolve) => setTimeout(resolve, 5));
  const follower = service.reconcile("config-change");

  release?.();
  const [leaderResult, followerResult] = await Promise.all([leader, follower]);

  // The follower must not be answered with the pre-build snapshot: it waits for
  // the follow-up build and sees a version produced after its request.
  assert.equal(builds, 2);
  assert.equal(followerResult.version, 2);
  assert.ok(leaderResult.version >= 1);
  // The follower receives the follow-up build's own result, not a flag on the
  // leader's stale one.
  assert.equal(followerResult.coalesced, false);
});

test("a build failure outside startup is visible in health", async () => {
  let attempts = 0;
  const state = { holder: true, listeners: [] as Array<() => void> };
  const lease = {
    get isHolder() {
      return state.holder;
    },
    get leaseToken() {
      return "processing-1";
    },
    acquire: async () => true,
    start: () => undefined,
    release: async () => undefined,
    onAcquired: (listener: () => void) => {
      state.listeners.push(listener);
    },
  } as unknown as ProcessingLease;

  const builder = {
    build: async () => {
      attempts += 1;
      if (attempts === 1) {
        return {
          snapshot: snapshot(1),
          timing: { startedAt: 0, finishedAt: 1, durationSeconds: 0.001 },
        };
      }
      throw new Error("mongo query failed");
    },
  } as unknown as SnapshotBuilder;

  const service = new ProcessingService(
    { shadowModeEnabled: true } as never,
    lease,
    builder,
    {
      validate: () => ({ valid: true, errors: [] }),
    } as unknown as SnapshotValidator,
    {
      initialiseVersionKeys: async () => EPOCH,
      nextVersion: async () => attempts,
      publish: async () => ({ published: true, reason: "ok" }),
    } as unknown as ShadowPublisher,
    {
      compareWithProduction: async () => ({
        compared: false,
        matches: false,
        parity: 0,
        comparedFields: 0,
        mismatches: 0,
        reason: "no-baseline",
      }),
    } as unknown as ShadowComparator,
    metrics(),
  );

  await service.reconcile("startup");
  assert.equal(service.status(), "healthy");

  await assert.rejects(service.reconcile("scheduled"), /mongo query failed/);
  assert.equal(service.status(), "unhealthy");
});
