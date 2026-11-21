import { Injectable } from "@nestjs/common";
import {
  BuildingSnapshot,
  ChargeSource,
  DashboardSnapshot,
  DEFAULT_DASHBOARD_TITLE,
  DASHBOARD_SETTING_KEYS,
  buildDashboardConfig,
  getEstimateChargeTime,
  getEstimateDischargeTime,
} from "../shared.js";
import {
  BuildingRecord,
  DashboardRepository,
  StationRecord,
  toPowerEstimationStation,
} from "../database/repositories/dashboard.repository.js";
import { OutagesScheduleRepository } from "../database/repositories/outages-schedule.repository.js";
import { SettingsRepository } from "../database/repositories/settings.repository.js";
import {
  ExtDataRecord,
  StationsDataRepository,
} from "../database/repositories/stations-data.repository.js";

export interface SnapshotBuildInput {
  epoch: number;
  version: number;
  generatedAt?: Date;
}

export interface SnapshotBuildTiming {
  startedAt: number;
  finishedAt: number;
  durationSeconds: number;
}

export interface SnapshotBuildResult {
  snapshot: DashboardSnapshot;
  timing: SnapshotBuildTiming;
}

const DISCHARGE_THRESHOLD_W = 200;
const CHARGE_THRESHOLD_W = 200;

const CHARGE_SOURCE_NONE: ChargeSource = "None";
const CHARGE_SOURCE_GRID: ChargeSource = "Grid";
const CHARGE_SOURCE_GENERATOR: ChargeSource = "Generator";
const CHARGE_SOURCE_RECUPERATION: ChargeSource = "Recuperation";

/**
 * Builds a `DashboardSnapshot v1` from MongoDB and Redis.
 *
 * The transformation is a direct port of
 * `back-end/app/services/dashboard_snapshot/service.py` plus
 * `shared/python/shared/services/dashboard/service.py`, so the shadow comparison
 * against the legacy producer is meaningful.
 */
@Injectable()
export class SnapshotBuilder {
  constructor(
    private readonly dashboard: DashboardRepository,
    private readonly stationsData: StationsDataRepository,
    private readonly settings: SettingsRepository,
    private readonly outages: OutagesScheduleRepository,
  ) {}

  async build(input: SnapshotBuildInput): Promise<SnapshotBuildResult> {
    const startedAt = Date.now();
    const generatedAt = input.generatedAt ?? new Date();

    const [config, buildings, allSchedules] = await Promise.all([
      this.buildConfig(),
      this.buildBuildings(),
      this.outages.getAllSchedules(),
    ]);

    const configuredQueue =
      config.outagesSchedule?.enable && config.outagesSchedule.queue
        ? config.outagesSchedule.queue
        : null;
    const outagesSchedules: DashboardSnapshot["outagesSchedules"] = {};
    if (configuredQueue !== null) {
      const unit = allSchedules[configuredQueue];
      if (unit) outagesSchedules[configuredQueue] = unit;
    }

    const snapshot: DashboardSnapshot = {
      epoch: input.epoch,
      version: input.version,
      generatedAt: generatedAt.toISOString(),
      buildings,
      config: {
        title: config.title,
        outagesSchedule: config.outagesSchedule,
      },
      outagesSchedules,
    };

    const finishedAt = Date.now();
    return {
      snapshot,
      timing: {
        startedAt,
        finishedAt,
        durationSeconds: (finishedAt - startedAt) / 1000,
      },
    };
  }

  private async buildConfig(): Promise<
    ReturnType<typeof buildDashboardConfig>
  > {
    const [title, enabled, region, dso, queue] = await Promise.all([
      this.settings.getLocalizableText(
        DASHBOARD_SETTING_KEYS.title,
        DEFAULT_DASHBOARD_TITLE,
      ),
      this.settings.getBoolean(
        DASHBOARD_SETTING_KEYS.outagesScheduleEnabled,
        false,
      ),
      this.settings.getValue(
        DASHBOARD_SETTING_KEYS.outagesScheduleRegion,
        null,
      ),
      this.settings.getValue(DASHBOARD_SETTING_KEYS.outagesScheduleDso, null),
      this.settings.getText(DASHBOARD_SETTING_KEYS.outagesScheduleQueue, ""),
    ]);
    return buildDashboardConfig({
      title,
      enabled,
      region,
      dso,
      queue,
    });
  }

  private async buildBuildings(): Promise<BuildingSnapshot[]> {
    const buildings = await this.dashboard.getBuildings();
    const stationIds = buildings
      .map((building) => building.stationId)
      .filter((id): id is string => id !== null);
    const stations = await this.dashboard.getStationsByIds(stationIds);
    const minutes = await this.settings.getNumber(
      "estimate_discharge_period_minutes",
      25,
    );

    const snapshots: BuildingSnapshot[] = [];
    for (const building of buildings) {
      const station = building.stationId
        ? (stations.get(building.stationId) ?? null)
        : null;
      snapshots.push(
        await this.buildBuildingSnapshot(building, station, minutes),
      );
    }
    return snapshots;
  }

  private async buildBuildingSnapshot(
    building: BuildingRecord,
    station: StationRecord | null,
    minutes: number,
  ): Promise<BuildingSnapshot> {
    const snapshot: BuildingSnapshot = {
      id: building.id,
      name: building.name,
      color: building.color,
      order: building.order,
      hasBoundStation: station !== null,
      chargeSource: CHARGE_SOURCE_NONE,
    };

    const observations = await this.getReporterStates(building.reportUserIds);
    if (observations.length > 0) {
      const trueCount = observations.filter((entry) => entry.gridState).length;
      snapshot.isGridAvailable = trueCount > 0;
      snapshot.gridAvailabilityPct = Math.trunc(
        (trueCount / observations.length) * 100,
      );
      snapshot.hasMixedReporterStates =
        trueCount > 0 && trueCount < observations.length;
    }

    if (station === null) return snapshot;

    const stationData = await this.stationsData.getLastStationData(station.id);
    if (stationData === null) return snapshot;

    const dischargePower = stationData.dischargePower ?? 0;
    const chargePower = stationData.chargePower ?? 0;
    const isDischarging = dischargePower > DISCHARGE_THRESHOLD_W;
    const isCharging = chargePower * -1 > CHARGE_THRESHOLD_W;

    const assumed = await this.stationsData.getAssumedConnectionStatus(
      station.id,
      this.reportIntervalSeconds,
      this.assumedOfflineReports,
    );
    snapshot.isOffline =
      station.connectionStatus === "ALL_OFFLINE" || assumed === "OFFLINE";
    snapshot.isCharging = isCharging;
    snapshot.isDischarging = isDischarging;
    snapshot.batteryPercent = stationData.batterySoc;

    const averageConsumptionW = await this.stationsData.getAverageColumn(
      station.id,
      "consumption_power",
      new Date(Date.now() - minutes * 60_000),
      new Date(),
    );
    snapshot.consumptionPower = `${(averageConsumptionW / 1000).toFixed(2)}`;

    const batteryCapacity = station.batteryCapacity ?? 0;
    const batterySoc = stationData.batterySoc ?? 0;

    if (isCharging && chargePower !== 0) {
      snapshot.chargeSource = CHARGE_SOURCE_GRID;
      const generationPower = stationData.generationPower ?? 0;
      const wirePower = stationData.wirePower ?? 0;
      if (generationPower > 0 && wirePower === 0) {
        snapshot.chargeSource = CHARGE_SOURCE_GENERATOR;
      }
      if (generationPower === 0 && wirePower === 0) {
        snapshot.chargeSource = CHARGE_SOURCE_RECUPERATION;
      }
      snapshot.batteryChargeTime = await getEstimateChargeTime(
        batteryCapacity,
        batterySoc,
        (chargePower / 1000) * -1,
        null,
        toPowerEstimationStation(station),
        this.settings,
      );
      snapshot.chargePower = (chargePower * -1) / 1000;
    }

    if (isDischarging && averageConsumptionW > 0) {
      snapshot.batteryDischargeTime = await getEstimateDischargeTime(
        batteryCapacity,
        batterySoc,
        averageConsumptionW / 1000,
        null,
        toPowerEstimationStation(station),
        this.settings,
      );
    }

    return snapshot;
  }

  private async getReporterStates(userIds: string[]): Promise<ExtDataRecord[]> {
    if (userIds.length === 0) return [];
    const byUser = await this.stationsData.getLastExtDataByUserIds(userIds);
    // Preserve the building's reporter order: the Python service gathers per
    // user and keeps that order when computing the availability percentage.
    return userIds
      .map((id) => byUser.get(id))
      .filter((entry): entry is ExtDataRecord => entry !== undefined);
  }

  /** Overridable in tests so the offline threshold is deterministic. */
  reportIntervalSeconds = 300;
  assumedOfflineReports = 2;
}
