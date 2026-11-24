import assert from "node:assert/strict";
import { test } from "node:test";
import { SchedulerService } from "../src/scheduler/scheduler.service.js";
import { SnapshotReconciliationJob } from "../src/scheduler/jobs/snapshot-reconciliation.job.js";
import type { ProcessingService } from "../src/processing/processing.service.js";
import type { MetricsService } from "../src/metrics/metrics.service.js";

const TICK_MS = 20;

function job(processing: {
  reconcile: (reason: string) => Promise<unknown>;
}): SnapshotReconciliationJob {
  return new SnapshotReconciliationJob(
    processing as unknown as ProcessingService,
  );
}

function scheduler(processing: {
  reconcile: (reason: string) => Promise<unknown>;
}): SchedulerService {
  const noop = () => undefined;
  return new SchedulerService(
    { shadowModeEnabled: true, reconciliationIntervalMs: TICK_MS } as never,
    job(processing),
    { jobExecution: noop } as unknown as MetricsService,
  );
}

test("the schedule fires on the configured interval, not on a cron minute", async () => {
  const reasons: string[] = [];
  const instance = job({
    reconcile: async (reason) => {
      reasons.push(reason);
      return { built: true, published: true };
    },
  });

  const timer = instance.schedule(TICK_MS, async (reason) => {
    reasons.push(reason);
  });
  try {
    await new Promise((resolve) => setTimeout(resolve, TICK_MS * 3));
  } finally {
    clearInterval(timer);
  }

  // A 5-field cron built from a seconds value would fire hourly; an interval
  // fires repeatedly inside a few tens of milliseconds.
  assert.ok(
    reasons.length >= 2,
    `expected at least 2 ticks, got ${reasons.length}`,
  );
  assert.deepEqual([...new Set(reasons)], ["scheduled"]);
});

test("runExclusive skips a tick while a build is still running", async () => {
  let release: (() => void) | undefined;
  const instance = scheduler({
    reconcile: () =>
      new Promise((resolve) => {
        release = () => resolve({ built: true, published: true });
      }),
  });

  const first = instance.runExclusive("scheduled");
  // The second tick lands while the first build is still in flight.
  await instance.runExclusive("scheduled");
  assert.equal(instance.isRunning, true);

  release?.();
  await first;
  assert.equal(instance.isRunning, false);
});

test("runExclusive records the error and clears the guard", async () => {
  const instance = scheduler({
    reconcile: async () => {
      throw new Error("mongo down");
    },
  });

  // The scheduler logs and records the failure rather than propagating it, so a
  // failing tick cannot take the timer down with it.
  await instance.runExclusive("scheduled");
  assert.equal(instance.isRunning, false);
});
