import assert from "node:assert/strict";
import { test } from "node:test";
import { ProcessingService } from "../src/processing/processing.service.js";
import type { ProcessingLease } from "../src/lease/processing-lease.service.js";
import type { SnapshotBuilder } from "../src/snapshot/snapshot.builder.js";
import type { SnapshotValidator } from "../src/snapshot/snapshot.validator.js";
import type { SnapshotPublisherLike } from "../src/processing/processing.service.js";
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
  publishEnabled?: boolean;
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
  } as unknown as SnapshotPublisherLike;

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
    {
      shadowModeEnabled: true,
      publishEnabled: options.publishEnabled,
    } as never,
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

test("the cutover flag is reported in the health details", async () => {
  const { service } = harness();
  // The harness config only enables shadow mode, so the instance must not claim
  // to own the production keys.
  assert.equal(service.details().publish_enabled, undefined);

  const publishing = harness({ publishEnabled: true });
  assert.equal(publishing.service.details().publish_enabled, true);
});

test("after the cutover the active publisher owns the epoch and the write", async () => {
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

  const calls: string[] = [];
  // The module hands the service the production publisher once the cutover is
  // on; the service must write through it and never touch the shadow namespace.
  const productionPublisher = {
    initialiseVersionKeys: async () => {
      calls.push("production:epoch");
      return EPOCH;
    },
    nextVersion: async () => {
      calls.push("production:version");
      return 7;
    },
    publish: async () => {
      calls.push("production:publish");
      return { published: true, reason: "ok" };
    },
  };

  const service = new ProcessingService(
    { shadowModeEnabled: true, publishEnabled: true } as never,
    lease,
    {
      build: async () => ({
        snapshot: snapshot(7),
        timing: { startedAt: 0, finishedAt: 1, durationSeconds: 0.001 },
      }),
    } as unknown as SnapshotBuilder,
    {
      validate: () => ({ valid: true, errors: [] }),
    } as unknown as SnapshotValidator,
    productionPublisher as unknown as SnapshotPublisherLike,
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

  const result = await service.reconcile("startup");

  assert.equal(result.published, true);
  assert.equal(result.version, 7);
  // Writing to the shadow namespace after the cutover would leave the BFFs on a
  // snapshot nobody updates.
  assert.deepEqual(calls, [
    "production:epoch",
    "production:version",
    "production:publish",
  ]);
});

test("after the cutover the comparison is skipped so parity is not self-reported", async () => {
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

  let compared = 0;
  const service = new ProcessingService(
    { shadowModeEnabled: true, publishEnabled: true } as never,
    lease,
    {
      build: async () => ({
        snapshot: snapshot(7),
        timing: { startedAt: 0, finishedAt: 1, durationSeconds: 0.001 },
      }),
    } as unknown as SnapshotBuilder,
    {
      validate: () => ({ valid: true, errors: [] }),
    } as unknown as SnapshotValidator,
    {
      initialiseVersionKeys: async () => EPOCH,
      nextVersion: async () => 7,
      publish: async () => ({ published: true, reason: "ok" }),
    } as unknown as SnapshotPublisherLike,
    {
      compareWithProduction: async () => {
        compared += 1;
        return {
          compared: true,
          matches: true,
          parity: 1,
          comparedFields: 1,
          mismatches: 0,
        };
      },
    } as unknown as ShadowComparator,
    metrics(),
  );

  const result = await service.reconcile("startup");

  // Comparing with the production key Processing just wrote would always report
  // parity 1.0, so the comparison is skipped and parity is reported as n/a.
  assert.equal(compared, 0);
  assert.equal(result.parity, null);
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

  // Startup kicks the first build off without awaiting it, so that a slow Mongo
  // cannot keep /health/live from binding; the failure still has to reach health.
  await service.onApplicationBootstrap();
  await new Promise((resolve) => setTimeout(resolve, 10));
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
    } as unknown as SnapshotPublisherLike,
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

/**
 * Builds a service whose first build is held open until `release()` is called,
 * optionally announcing when the builder is entered.
 */
function serviceWithHeldFirstBuild(onBuild?: (attempt: number) => void) {
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
      const attempt = builds;
      onBuild?.(attempt);
      if (attempt === 1) {
        await new Promise<void>((resolve) => {
          release = resolve;
        });
      }
      return {
        snapshot: snapshot(attempt),
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
    } as unknown as SnapshotPublisherLike,
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

  return {
    service,
    release: () => release?.(),
    builds: () => builds,
  };
}

test("every waiter during one build settles, not just the last one", async () => {
  const { service, release } = serviceWithHeldFirstBuild();

  const leader = service.reconcile("config-change");
  // Let the leader reach its first await inside the builder.
  await new Promise((resolve) => setTimeout(resolve, 5));
  // Two callers arrive during the same build: a single resolver slot would
  // answer only the second one and leave the first pending forever.
  const first = service.reconcile("scheduled");
  const second = service.reconcile("scheduled");

  release?.();
  const results = await Promise.all([leader, first, second]);

  assert.equal(results.length, 3);
  // Both mid-build callers are answered by the one shared follow-up build.
  assert.equal(results[1].version, 2);
  assert.equal(results[2].version, 2);
});

test("a failing follow-up build rejects every waiter instead of hanging", async () => {
  const { service, release } = serviceWithHeldFirstBuild((attempt) => {
    if (attempt === 2) throw new Error("follow-up build failed");
  });

  const leader = service.reconcile("config-change");
  await new Promise((resolve) => setTimeout(resolve, 5));
  const first = service.reconcile("scheduled");
  const second = service.reconcile("scheduled");

  release?.();
  await leader;
  await assert.rejects(first, /follow-up build failed/);
  await assert.rejects(second, /follow-up build failed/);
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
    } as unknown as SnapshotPublisherLike,
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

test("onApplicationBootstrap resolves while the first build is still held", async () => {
  let releaseFirst!: () => void;
  const firstBuildStarted = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  const { service, release } = serviceWithHeldFirstBuild(() => {
    releaseFirst();
  });

  // `onApplicationBootstrap` runs before the HTTP server binds, so awaiting the
  // first build here would leave /health/live unreachable for the whole build.
  await service.onApplicationBootstrap();
  await firstBuildStarted;
  assert.equal(service.details().last_build_at, null);

  const settled = service.inFlightSettled();
  release?.();
  await settled;
  assert.ok(service.details().last_build_at !== null);
});

test("a request arriving after the shutdown started fails fast", async () => {
  const { service } = harness();
  await service.onModuleDestroy();

  await assert.rejects(service.reconcile("scheduled"), /shutting down/);
});

test("a shutdown mid-build rejects the waiters and starts no follow-up", async () => {
  const { service, release, builds } = serviceWithHeldFirstBuild();

  const leader = service.reconcile("config-change");
  await new Promise((resolve) => setTimeout(resolve, 5));
  const follower = service.reconcile("scheduled");

  await service.onModuleDestroy();
  release?.();

  await leader;
  // The waiter must learn the real reason: a follow-up started after the Redis
  // clients close would reject it with a connection error instead.
  await assert.rejects(follower, /shutting down/);
  assert.equal(builds(), 1);
});
