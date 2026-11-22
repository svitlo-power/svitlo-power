import assert from "node:assert/strict";
import { test } from "node:test";
import { SnapshotBuilder } from "../src/snapshot/snapshot.builder.js";
import type {
  BuildingRecord,
  DashboardRepository,
  StationRecord,
} from "../src/database/repositories/dashboard.repository.js";
import type { StationsDataRepository } from "../src/database/repositories/stations-data.repository.js";
import type { SettingsRepository } from "../src/database/repositories/settings.repository.js";
import type { OutagesScheduleRepository } from "../src/database/repositories/outages-schedule.repository.js";

const BUILDING_ID = "507f1f77bcf86cd799439011";
const STATION_ID = "507f1f77bcf86cd799439012";

function building(overrides: Partial<BuildingRecord> = {}): BuildingRecord {
  return {
    id: BUILDING_ID,
    name: { en: "Home" },
    color: "#fff",
    enabled: true,
    order: 1,
    stationId: STATION_ID,
    reportUserIds: [],
    ...overrides,
  };
}

function station(overrides: Partial<StationRecord> = {}): StationRecord {
  return {
    id: STATION_ID,
    connectionStatus: "NORMAL",
    batteryCapacity: 10,
    dischargeTargetSoc: null,
    chargeTargetSoc: null,
    ...overrides,
  };
}

interface FakeOptions {
  buildings?: BuildingRecord[];
  stations?: StationRecord[];
  settings?: Record<string, unknown>;
  lastStationData?: Record<string, unknown> | null;
  averageConsumptionW?: number;
  extData?: Map<string, { gridState: boolean; receivedAt: Date }>;
  schedules?: Record<string, unknown>;
}

function builder(options: FakeOptions = {}): SnapshotBuilder {
  const buildings = options.buildings ?? [building()];
  const stations = new Map(
    (options.stations ?? [station()]).map((entry) => [entry.id, entry]),
  );
  const settings = options.settings ?? {};

  const dashboard = {
    getBuildings: async () => buildings,
    getStationsByIds: async () => stations,
  } as unknown as DashboardRepository;

  const stationsData = {
    getLastStationData: async () =>
      options.lastStationData === undefined
        ? {
            batterySoc: 55,
            chargePower: 0,
            dischargePower: 0,
            generationPower: 0,
            wirePower: 0,
            consumptionPower: 500,
            lastUpdateTime: new Date(),
          }
        : options.lastStationData,
    getAverageColumn: async () => options.averageConsumptionW ?? 0,
    getLastExtDataByUserIds: async () => options.extData ?? new Map(),
    getAssumedConnectionStatus: async () => "NORMAL" as const,
  } as unknown as StationsDataRepository;

  const settingsRepo = {
    getLocalizableText: async (
      _key: string,
      fallback: Record<string, string>,
    ) => (settings.title as Record<string, string>) ?? fallback,
    getBoolean: async (key: string) => (settings[key] as boolean) ?? false,
    getValue: async (key: string) => settings[key] ?? null,
    getText: async (key: string) => (settings[key] as string) ?? "",
    getNumber: async () => 25,
    getInt: async (_key: string, fallback: number) => fallback,
  } as unknown as SettingsRepository;

  const outages = {
    getAllSchedules: async () => options.schedules ?? {},
  } as unknown as OutagesScheduleRepository;

  return new SnapshotBuilder(dashboard, stationsData, settingsRepo, outages);
}

test("a building without a station reports only static fields", async () => {
  const { snapshot } = await builder({
    buildings: [building({ stationId: null })],
  }).build({ epoch: 1_700_000_000_000, version: 1 });

  assert.equal(snapshot.buildings.length, 1);
  const [entry] = snapshot.buildings;
  assert.equal(entry.hasBoundStation, false);
  assert.equal(entry.chargeSource, "None");
  // Optional fields are present but null, matching the legacy Pydantic model.
  assert.equal(entry.batteryPercent, null);
  assert.equal(entry.isOffline, null);
});

test("a building whose station has no measurements stops after the reporter state", async () => {
  const { snapshot } = await builder({ lastStationData: null }).build({
    epoch: 1_700_000_000_000,
    version: 1,
  });

  const [entry] = snapshot.buildings;
  assert.equal(entry.hasBoundStation, true);
  // Optional fields are present but null, matching the legacy Pydantic model.
  assert.equal(entry.batteryPercent, null);
  assert.equal(entry.consumptionPower, null);
});

test("reporter states drive grid availability and the mixed-state flag", async () => {
  const extData = new Map([
    ["507f1f77bcf86cd799439101", { gridState: true, receivedAt: new Date() }],
    ["507f1f77bcf86cd799439102", { gridState: false, receivedAt: new Date() }],
  ]);
  const { snapshot } = await builder({
    buildings: [building({ reportUserIds: [...extData.keys()] })],
    extData,
  }).build({ epoch: 1_700_000_000_000, version: 1 });

  const [entry] = snapshot.buildings;
  assert.equal(entry.isGridAvailable, true);
  assert.equal(entry.gridAvailabilityPct, 50);
  assert.equal(entry.hasMixedReporterStates, true);
});

test("charging distinguishes grid, generator and recuperation", async () => {
  const cases: Array<{
    generationPower: number;
    wirePower: number;
    expected: string;
  }> = [
    { generationPower: 0, wirePower: 100, expected: "Grid" },
    { generationPower: 500, wirePower: 0, expected: "Generator" },
    { generationPower: 0, wirePower: 0, expected: "Recuperation" },
  ];

  for (const item of cases) {
    const { snapshot } = await builder({
      lastStationData: {
        batterySoc: 55,
        chargePower: -3000,
        dischargePower: 0,
        generationPower: item.generationPower,
        wirePower: item.wirePower,
        consumptionPower: 0,
        lastUpdateTime: new Date(),
      },
    }).build({ epoch: 1_700_000_000_000, version: 1 });

    const [entry] = snapshot.buildings;
    assert.equal(entry.isCharging, true);
    assert.equal(entry.chargeSource, item.expected);
    assert.equal(entry.chargePower, 3);
  }
});

test("discharging above the 200 W threshold reports a discharge estimate", async () => {
  const { snapshot } = await builder({
    lastStationData: {
      batterySoc: 55,
      chargePower: 0,
      dischargePower: 3000,
      generationPower: 0,
      wirePower: 0,
      consumptionPower: 0,
      lastUpdateTime: new Date(),
    },
    averageConsumptionW: 1000,
  }).build({ epoch: 1_700_000_000_000, version: 1 });

  const [entry] = snapshot.buildings;
  assert.equal(entry.isDischarging, true);
  // 10 kWh battery at 55% down to the 10% target: 4.5 kWh at 1 kW → 04:30.
  assert.equal(entry.batteryDischargeTime, "04:30");
  assert.equal(entry.consumptionPower, "1.00");
});

test("a station reporting ALL_OFFLINE is marked offline", async () => {
  const { snapshot } = await builder({
    stations: [station({ connectionStatus: "ALL_OFFLINE" })],
  }).build({ epoch: 1_700_000_000_000, version: 1 });

  assert.equal(snapshot.buildings[0].isOffline, true);
});

test("the outages schedule is only included for the configured queue", async () => {
  const schedules = {
    "1.1": { days: [], updatedOn: "2026-01-01T00:00:00.000Z" },
    "2.2": { days: [], updatedOn: "2026-01-01T00:00:00.000Z" },
  };
  const { snapshot } = await builder({
    settings: {
      dashboard_outages_schedule_enabled: true,
      dashboard_outages_schedule_region: 25,
      dashboard_outages_schedule_dso: 902,
      dashboard_outages_schedule_queue: "1.1",
    },
    schedules,
  }).build({ epoch: 1_700_000_000_000, version: 1 });

  assert.equal(snapshot.config.outagesSchedule?.enable, true);
  assert.deepEqual(Object.keys(snapshot.outagesSchedules), ["1.1"]);
});

test("a disabled outages schedule omits all queues", async () => {
  const { snapshot } = await builder({
    settings: {
      dashboard_outages_schedule_enabled: false,
      dashboard_outages_schedule_region: 25,
      dashboard_outages_schedule_dso: 902,
      dashboard_outages_schedule_queue: "1.1",
    },
    schedules: { "1.1": { days: [], updatedOn: "2026-01-01T00:00:00.000Z" } },
  }).build({ epoch: 1_700_000_000_000, version: 1 });

  assert.equal(snapshot.config.outagesSchedule?.enable, false);
  assert.deepEqual(snapshot.outagesSchedules, {});
});

test("an empty database produces a valid empty snapshot", async () => {
  const { snapshot, timing } = await builder({ buildings: [] }).build({
    epoch: 1_700_000_000_000,
    version: 1,
  });

  assert.deepEqual(snapshot.buildings, []);
  assert.deepEqual(snapshot.outagesSchedules, {});
  assert.equal(snapshot.epoch, 1_700_000_000_000);
  assert.equal(snapshot.version, 1);
  assert.ok(timing.durationSeconds >= 0);
});
