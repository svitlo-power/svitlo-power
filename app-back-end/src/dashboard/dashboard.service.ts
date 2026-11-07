import {
  BadRequestException,
  Inject,
  Injectable,
  UnprocessableEntityException,
} from "@nestjs/common";
import {
  Building,
  BuildingSnapshot,
  BuildingSummary,
  BuildingWithSummary,
  DashboardConfig,
  InternalApiClient,
  PowerLogs,
} from "../shared.js";
import { parseIsoDateTime } from "../http/iso-date.js";
import { SnapshotService } from "../snapshots/snapshot.service.js";
import { INTERNAL_API } from "../tokens.js";
import {
  BuildingIdsDto,
  objectIdPattern,
  PowerLogsDto,
} from "./dashboard.dto.js";

export interface MobileDashboardConfig {
  title: DashboardConfig["title"];
  enableOutagesSchedule: boolean;
  outagesScheduleQueue: string | null;
}

@Injectable()
export class DashboardService {
  constructor(
    @Inject(INTERNAL_API) private readonly api: InternalApiClient,
    private readonly snapshots: SnapshotService,
  ) {}

  async getBuildings(): Promise<Building[]> {
    const snapshot = this.snapshots.getActiveSnapshot();
    if (snapshot) return snapshot.buildings.map(toBuilding);
    return this.api.getBuildings();
  }

  async getBuildingSummaries(body: BuildingIdsDto): Promise<BuildingSummary[]> {
    const snapshot = this.snapshots.getActiveSnapshot();
    if (snapshot) {
      const known = new Set(snapshot.buildings.map((building) => building.id));
      if (body.buildingIds.every((id) => known.has(id))) {
        const requested = new Set(body.buildingIds);
        return snapshot.buildings
          .filter((building) => requested.has(building.id))
          .map(toSummary);
      }
    }
    return this.api.getBuildingSummaries(body.buildingIds);
  }

  async getBuildingsWithSummary(): Promise<BuildingWithSummary[]> {
    const snapshot = this.snapshots.getActiveSnapshot();
    if (snapshot)
      return snapshot.buildings.map((building) => ({
        ...toBuilding(building),
        ...toSummary(building),
      }));
    return this.api.getBuildingsWithSummary();
  }

  async getDashboardConfig(): Promise<MobileDashboardConfig> {
    const snapshot = this.snapshots.getActiveSnapshot();
    const config = snapshot?.config ?? (await this.api.getDashboardConfig());
    const schedule = config.outagesSchedule;
    return {
      title: config.title,
      enableOutagesSchedule: Boolean(schedule?.enable),
      outagesScheduleQueue: schedule?.queue ?? null,
    };
  }

  async getPowerLogs(
    buildingId: string,
    body: PowerLogsDto,
  ): Promise<PowerLogs> {
    if (!objectIdPattern.test(buildingId)) {
      // Same shape as FastAPI's path-parameter validation error.
      throw new UnprocessableEntityException({
        detail: [
          {
            loc: ["path", "building_id"],
            msg: "Invalid ObjectId",
            type: "value_error",
          },
        ],
      });
    }
    const start = parseIsoDateTime(body.startDate);
    const end = parseIsoDateTime(body.endDate);
    if (start === null || end === null)
      throw new BadRequestException("Invalid date format");
    if (start >= end)
      throw new BadRequestException("startDate must be before endDate");
    return this.api.getPowerLogs(
      buildingId,
      body.startDate as string,
      body.endDate as string,
    );
  }
}

function toBuilding(building: BuildingSnapshot): Building {
  return {
    id: building.id,
    name: building.name,
    color: building.color,
    hasBoundStation: building.hasBoundStation,
    order: building.order,
  };
}

function toSummary(building: BuildingSnapshot): BuildingSummary {
  return {
    id: building.id,
    isGridAvailable: building.isGridAvailable ?? null,
    gridAvailabilityPct: building.gridAvailabilityPct ?? null,
    hasMixedReporterStates: building.hasMixedReporterStates ?? null,
    batteryPercent: building.batteryPercent ?? null,
    isCharging: building.isCharging ?? null,
    isDischarging: building.isDischarging ?? null,
    isOffline: building.isOffline ?? null,
    batteryDischargeTime: building.batteryDischargeTime ?? null,
    batteryChargeTime: building.batteryChargeTime ?? null,
    consumptionPower: building.consumptionPower ?? null,
    chargeSource: building.chargeSource,
    chargePower: building.chargePower ?? null,
  };
}
