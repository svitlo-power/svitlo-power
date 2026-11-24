import assert from "node:assert/strict";
import { test } from "node:test";
import { SnapshotReconciliationJob } from "../src/scheduler/jobs/snapshot-reconciliation.job.js";
import type { ProcessingService } from "../src/processing/processing.service.js";

const TICK_MS = 20;

function job(processing: {
  reconcile: (reason: string) => Promise<unknown>;
}): SnapshotReconciliationJob {
  return new SnapshotReconciliationJob(
    processing as unknown as ProcessingService,
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
  const instance = job({
    reconcile: () =>
      new Promise((resolve) => {
        release = () => resolve({ built: true, published: true });
      }),
  });

  const first = instance.runExclusive("scheduled");
  await instance.runExclusive("scheduled");
  assert.equal(instance.isRunning, true);

  release?.();
  await first;
  assert.equal(instance.isRunning, false);
});

test("runExclusive swallows the error after recording it", async () => {
  const instance = job({
    reconcile: async () => {
      throw new Error("mongo down");
    },
  });

  await instance.runExclusive("scheduled");
  assert.equal(instance.isRunning, false);
});
