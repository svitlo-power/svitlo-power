import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildDashboardConfig,
  changedSections,
  diffSnapshots,
  getEstimateChargeTime,
  getEstimateDischargeTime,
  keepOnlyDefiniteSlots,
  normalizeScheduleId,
} from "../src/index.js";
import type { DashboardSnapshot } from "../src/index.js";

test("schedule id normalisation matches the Python helper", () => {
  assert.equal(normalizeScheduleId(true), null);
  assert.equal(normalizeScheduleId(false), null);
  assert.equal(normalizeScheduleId(0), null);
  assert.equal(normalizeScheduleId(-3), null);
  assert.equal(normalizeScheduleId(25), 25);
  assert.equal(normalizeScheduleId(" 25 "), 25);
  assert.equal(normalizeScheduleId("   "), null);
  assert.equal(normalizeScheduleId(""), null);
  assert.equal(normalizeScheduleId("Kyiv"), "Kyiv");
  assert.equal(normalizeScheduleId("0"), "0");
  assert.equal(normalizeScheduleId(null), null);
  assert.equal(normalizeScheduleId(undefined), null);
});

test("dashboard config only enables a fully configured schedule", () => {
  const disabled = buildDashboardConfig({
    title: { en: "Dashboard" },
    enabled: true,
    region: 25,
    dso: 902,
    queue: "",
  });
  assert.equal(disabled.outagesSchedule.enable, false);
  assert.equal(disabled.enableOutagesSchedule, false);
  assert.equal(disabled.outagesSchedule.queue, null);

  const enabled = buildDashboardConfig({
    title: { en: "Dashboard" },
    enabled: true,
    region: "25",
    dso: "Kyiv",
    queue: "1.1",
  });
  assert.equal(enabled.outagesSchedule.enable, true);
  assert.equal(enabled.outagesSchedule.regionId, 25);
  assert.equal(enabled.outagesSchedule.dsoId, "Kyiv");
  assert.equal(enabled.outagesSchedule.queue, "1.1");
  assert.equal(enabled.enableOutagesSchedule, true);
});

test("outage schedules keep only definite slots", () => {
  const result = keepOnlyDefiniteSlots({
    "1.1": {
      days: [
        {
          slots: [
            { start: 0, end: 60, type: "Definite" },
            { start: 60, end: 120, type: "NotPlanned" },
          ],
        },
      ],
    },
  });
  assert.deepEqual(result["1.1"].days[0].slots, [
    { start: 0, end: 60, type: "Definite" },
  ]);
});

test("power estimators format HH:MM exactly like the Python producer", async () => {
  // 10 kWh battery at 50% down to the 10% target: 4 kWh at 10 kW → 24 minutes.
  assert.equal(await getEstimateDischargeTime(10, 50, 10, 10), "00:24");
  // Zero average consumption short-circuits to 00:00.
  assert.equal(await getEstimateDischargeTime(10, 50, 0, 10), "00:00");
  // Charging 10 kWh from 50% to 97% at 5 kW: 4.7 kWh → 56 minutes.
  assert.equal(await getEstimateChargeTime(10, 50, 5, 97), "00:56");
  assert.equal(await getEstimateChargeTime(10, 50, 0, 97), "00:00");
});

test("power estimators prefer the station SOC overrides", async () => {
  const station = { discharge_target_soc: 20, charge_target_soc: 80 };
  // 10 kWh battery at 50% down to 20%: 3 kWh at 10 kW → 18 minutes.
  assert.equal(
    await getEstimateDischargeTime(10, 50, 10, null, station),
    "00:18",
  );
  // 10 kWh battery from 50% up to 80% at 5 kW: 3 kWh → 36 minutes.
  assert.equal(await getEstimateChargeTime(10, 50, 5, null, station), "00:36");
});

test("power estimators fall back to the settings service", async () => {
  const settings = {
    getInt: (key: string, fallback: number) =>
      key === "discharge_target_soc" ? 40 : fallback,
  };
  // 10 kWh battery at 50% down to 40%: 1 kWh at 10 kW → 6 minutes.
  assert.equal(
    await getEstimateDischargeTime(10, 50, 10, null, null, settings),
    "00:06",
  );
});

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
        isGridAvailable: true,
        gridAvailabilityPct: 100,
        hasMixedReporterStates: false,
        isCharging: false,
        isDischarging: false,
        isOffline: false,
        batteryPercent: 55,
        consumptionPower: "1.00",
        batteryDischargeTime: null,
        batteryChargeTime: null,
        chargeSource: "None",
        chargePower: null,
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
    outagesSchedules: {
      "1.1": {
        days: [],
        updatedOn: "2026-01-01T00:00:00.000Z",
      },
    },
    ...overrides,
  };
}

test("identical snapshots compare as a full parity match", () => {
  const diff = diffSnapshots(snapshot(), snapshot());
  assert.equal(diff.matches, true);
  assert.equal(diff.parity, 1);
  assert.deepEqual(diff.mismatches, []);
});

test("snapshot diff reports the exact field that differs", () => {
  const baseline = snapshot();
  const candidate = snapshot();
  candidate.buildings[0].batteryPercent = 40;
  candidate.buildings[0].chargeSource = "Grid";

  const diff = diffSnapshots(baseline, candidate);
  assert.equal(diff.matches, false);
  assert.deepEqual(
    diff.mismatches.map((mismatch) => mismatch.field),
    [
      "507f1f77bcf86cd799439011.batteryPercent",
      "507f1f77bcf86cd799439011.chargeSource",
    ],
  );
  assert.equal(diff.mismatches[0].section, "summary");
  assert.ok(diff.parity < 1);
});

test("snapshot diff matches buildings by id, not by position", () => {
  const baseline = snapshot();
  const reordered = snapshot();
  reordered.buildings = [
    { ...reordered.buildings[0], id: "507f1f77bcf86cd799439099" },
    reordered.buildings[0],
  ];

  const diff = diffSnapshots(baseline, reordered);
  assert.equal(diff.matches, false);
  // Only the added/removed ids are reported; the shared building is untouched.
  assert.deepEqual(diff.missingBuildings, []);
  assert.deepEqual(diff.extraBuildings, ["507f1f77bcf86cd799439099"]);
  assert.deepEqual(
    diff.mismatches.map((mismatch) => mismatch.field),
    ["buildings:length", "buildings.507f1f77bcf86cd799439099"],
  );
});

test("snapshot diff reports a missing building as its own mismatch", () => {
  const baseline = snapshot();
  const candidate = snapshot();
  candidate.buildings = [];

  const diff = diffSnapshots(baseline, candidate);
  assert.deepEqual(diff.missingBuildings, ["507f1f77bcf86cd799439011"]);
  assert.deepEqual(diff.extraBuildings, []);
  assert.deepEqual(
    diff.mismatches.map((mismatch) => mismatch.field),
    ["buildings:length", "buildings.507f1f77bcf86cd799439011"],
  );
});

test("snapshot diff ignores generatedAt, epoch and version", () => {
  const baseline = snapshot();
  const candidate = snapshot({
    epoch: 1_700_000_000_500,
    version: 42,
    generatedAt: "2026-01-01T00:00:05.000Z",
  });
  assert.equal(diffSnapshots(baseline, candidate).matches, true);
});

test("changed sections reports all four on the first build", () => {
  assert.deepEqual(changedSections(null, snapshot()), [
    "buildings",
    "summary",
    "config",
    "outages",
  ]);
});

test("changed sections separates static building fields from summaries", () => {
  const baseline = snapshot();
  const renamed = snapshot();
  renamed.buildings[0].name = { en: "Cottage" };
  assert.deepEqual(changedSections(baseline, renamed), ["buildings"]);

  const measured = snapshot();
  measured.buildings[0].batteryPercent = 20;
  assert.deepEqual(changedSections(baseline, measured), ["summary"]);

  const reconfigured = snapshot();
  reconfigured.config = { title: { en: "Dashboard" }, outagesSchedule: null };
  assert.deepEqual(changedSections(baseline, reconfigured), ["config"]);

  const rescheduled = snapshot();
  rescheduled.outagesSchedules = {};
  assert.deepEqual(changedSections(baseline, rescheduled), ["outages"]);

  assert.deepEqual(changedSections(baseline, snapshot()), []);
});
