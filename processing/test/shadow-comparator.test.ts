import assert from "node:assert/strict";
import { test } from "node:test";
import type { DashboardSnapshot } from "../src/shared.js";
import { ShadowComparator } from "../src/shadow/shadow-comparator.service.js";
import type { MetricsService } from "../src/metrics/metrics.service.js";

function metrics(): MetricsService {
  const noop = () => undefined;
  return {
    setShadowParity: noop,
    shadowMismatch: noop,
    shadowComparison: noop,
  } as unknown as MetricsService;
}

function snapshot(
  overrides: Partial<DashboardSnapshot> = {},
): DashboardSnapshot {
  return {
    epoch: 1_700_000_000_000,
    version: 1,
    generatedAt: "2026-01-01T00:00:00.000Z",
    buildings: [],
    config: { title: { en: "Dashboard" }, outagesSchedule: null },
    outagesSchedules: {},
    ...overrides,
  };
}

function comparator(redis: {
  get: (key: string) => Promise<string | null>;
}): ShadowComparator {
  return new ShadowComparator(redis as never, metrics());
}

test("an empty production cache is reported as having no baseline", async () => {
  const result = await comparator({
    get: async () => null,
  }).compareWithProduction(snapshot());
  assert.equal(result.compared, false);
  assert.equal(result.reason, "no-baseline");
});

test("a malformed production snapshot is reported as an invalid baseline", async () => {
  const result = await comparator({
    get: async () => "{not json",
  }).compareWithProduction(snapshot());
  assert.equal(result.compared, false);
  assert.equal(result.reason, "invalid-baseline");
});

test("a matching production snapshot reports full parity", async () => {
  const baseline = snapshot();
  const result = await comparator({
    get: async () => JSON.stringify(baseline),
  }).compareWithProduction(baseline);
  assert.equal(result.compared, true);
  assert.equal(result.matches, true);
  assert.equal(result.parity, 1);
  assert.equal(result.mismatches, 0);
});

test("a differing production snapshot reports the mismatch count", async () => {
  const baseline = snapshot();
  const candidate = snapshot();
  candidate.buildings = [
    {
      id: "507f1f77bcf86cd799439011",
      name: { en: "Home" },
      color: "#fff",
      order: 1,
      hasBoundStation: true,
      chargeSource: "Grid",
    },
  ];
  const result = await comparator({
    get: async () => JSON.stringify(baseline),
  }).compareWithProduction(candidate);
  assert.equal(result.compared, true);
  assert.equal(result.matches, false);
  // The added building shows up as a length mismatch plus the missing entry.
  assert.equal(result.mismatches, 2);
  assert.ok(result.parity < 1);
});

test("a Redis read failure is reported instead of throwing", async () => {
  const result = await comparator({
    get: async () => {
      throw new Error("connection closed");
    },
  }).compareWithProduction(snapshot());
  assert.equal(result.compared, false);
  assert.equal(result.reason, "read-error");
});
