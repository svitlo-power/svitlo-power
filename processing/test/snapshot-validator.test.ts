import assert from "node:assert/strict";
import { test } from "node:test";
import type { DashboardSnapshot } from "../src/shared.js";
import { SnapshotValidator } from "../src/snapshot/snapshot.validator.js";

const config = { version: "test" } as never;

function snapshot(
  overrides: Partial<DashboardSnapshot> = {},
): DashboardSnapshot {
  return {
    epoch: 1_700_000_000_000,
    version: 1,
    generatedAt: "2026-01-01T00:00:00.000Z",
    buildings: [
      {
        id: "507f1f77bcf86cd799439011",
        name: { en: "Home" },
        color: "#fff",
        order: 1,
        hasBoundStation: true,
        chargeSource: "None",
      },
    ],
    config: {
      title: { en: "Dashboard" },
      outagesSchedule: {
        enable: true,
        regionId: 25,
        dsoId: 902,
        queue: "1.1",
      },
    },
    outagesSchedules: {},
    ...overrides,
  };
}

test("a well-formed snapshot validates", () => {
  const result = new SnapshotValidator(config).validate(snapshot());
  assert.deepEqual(result, { valid: true, errors: [] });
});

test("an empty-cache snapshot with no buildings still validates", () => {
  const result = new SnapshotValidator(config).validate(
    snapshot({ buildings: [], outagesSchedules: {} }),
  );
  assert.equal(result.valid, true);
});

test("epoch, version and generatedAt are required", () => {
  const validator = new SnapshotValidator(config);
  const bad = snapshot({ epoch: 0, version: 0, generatedAt: "yesterday" });
  const result = validator.validate(bad);
  assert.equal(result.valid, false);
  assert.ok(result.errors.includes("epoch must be a positive integer"));
  assert.ok(result.errors.includes("version must be a positive integer"));
  assert.ok(
    result.errors.includes("generatedAt must be an ISO 8601 timestamp"),
  );
});

test("building ids must be 24-char hex ObjectIds", () => {
  const bad = snapshot();
  bad.buildings[0].id = "not-an-object-id";
  const result = new SnapshotValidator(config).validate(bad);
  assert.equal(result.valid, false);
  assert.ok(
    result.errors.includes("buildings[0].id must be a 24-char hex ObjectId"),
  );
});

test("an enabled outages schedule requires a queue", () => {
  const bad = snapshot();
  bad.config.outagesSchedule = {
    enable: true,
    regionId: 25,
    dsoId: 902,
    queue: null,
  };
  const result = new SnapshotValidator(config).validate(bad);
  assert.equal(result.valid, false);
  assert.ok(
    result.errors.includes(
      "config.outagesSchedule.queue is required when enabled",
    ),
  );
});

test("unsupported locales in the dashboard title are rejected", () => {
  const bad = snapshot();
  bad.config.title = { en: "Dashboard", de: "Uebersicht" } as never;
  const result = new SnapshotValidator(config).validate(bad);
  assert.equal(result.valid, false);
  assert.ok(result.errors.includes("config.title has unsupported locale 'de'"));
});
