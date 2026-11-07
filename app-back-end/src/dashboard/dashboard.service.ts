import {
  BadRequestException,
  Inject,
  Injectable,
  UnprocessableEntityException,
} from "@nestjs/common";
import {
  Building,
  BuildingSummary,
  BuildingWithSummary,
  DashboardConfig,
  InternalApiClient,
} from "../../../shared/typescript/src/index.js";
import { SnapshotService } from "../snapshots/snapshot.service.js";
import { INTERNAL_API } from "../tokens.js";
import { BuildingIdsDto, PowerLogsDto } from "./dashboard.dto.js";

@Injectable()
export class DashboardService {
  constructor(
    @Inject(INTERNAL_API) private readonly api: InternalApiClient,
    private readonly snapshots: SnapshotService,
  ) {}

  async getBuildings(): Promise<Building[]> {
    const snapshot = this.snapshots.getActiveSnapshot();
    if (snapshot)
      return snapshot.buildings.map((building) => this.basicBuilding(building));
    return this.api.getBuildings();
  }

  async getBuildingSummaries(body: BuildingIdsDto): Promise<BuildingSummary[]> {
    const snapshot = this.snapshots.getActiveSnapshot();
    if (snapshot) {
      const byId = new Map(
        snapshot.buildings.map((building) => [building.id, building]),
      );
      if (body.buildingIds.every((id) => byId.has(id))) {
        const requested = new Set(body.buildingIds);
        return snapshot.buildings
          .filter((building) => requested.has(building.id))
          .map((building) => this.summary(building));
      }
    }
    return this.api.getBuildingSummaries(body.buildingIds);
  }

  async getBuildingsWithSummary(): Promise<BuildingWithSummary[]> {
    const snapshot = this.snapshots.getActiveSnapshot();
    if (snapshot)
      return snapshot.buildings.map((building) => ({
        ...this.basicBuilding(building),
        ...this.summary(building),
      }));
    return this.api.getBuildingsWithSummary();
  }

  async getDashboardConfig(): Promise<{
    title: DashboardConfig["title"];
    enableOutagesSchedule: boolean;
    outagesScheduleQueue: string | null;
  }> {
    const snapshot = this.snapshots.getActiveSnapshot();
    const config = snapshot?.config ?? (await this.api.getDashboardConfig());
    const schedule = config.outagesSchedule;
    return {
      title: config.title,
      enableOutagesSchedule: Boolean(schedule?.enable),
      outagesScheduleQueue: schedule?.queue ?? null,
    };
  }

  async getPowerLogs(buildingId: string, body: PowerLogsDto) {
    if (!/^[0-9a-fA-F]{24}$/.test(buildingId)) {
      throw new UnprocessableEntityException("Invalid building id");
    }
    if (!body.startDate || !body.endDate)
      throw new BadRequestException("Invalid date format");
    const start = Date.parse(body.startDate);
    const end = Date.parse(body.endDate);
    if (!Number.isFinite(start) || !Number.isFinite(end)) {
      throw new BadRequestException("Invalid date format");
    }
    if (start >= end)
      throw new BadRequestException("startDate must be before endDate");
    return this.api.getPowerLogs(buildingId, body.startDate, body.endDate);
  }

  private basicBuilding(
    building: Record<string, unknown> & { id: string },
  ): Building {
    return {
      id: building.id,
      name: building.name as Record<string, string>,
      color: String(building.color),
      hasBoundStation: Boolean(building.hasBoundStation),
      order: Number(building.order),
    };
  }

  private summary(
    building: Record<string, unknown> & { id: string },
  ): BuildingSummary {
    return {
      id: building.id,
      isGridAvailable:
        (building.isGridAvailable as boolean | null | undefined) ?? null,
      gridAvailabilityPct:
        (building.gridAvailabilityPct as number | null | undefined) ?? null,
      hasMixedReporterStates:
        (building.hasMixedReporterStates as boolean | null | undefined) ?? null,
      batteryPercent:
        (building.batteryPercent as number | null | undefined) ?? null,
      isCharging: (building.isCharging as boolean | null | undefined) ?? null,
      isDischarging:
        (building.isDischarging as boolean | null | undefined) ?? null,
      isOffline: (building.isOffline as boolean | null | undefined) ?? null,
      batteryDischargeTime:
        (building.batteryDischargeTime as string | null | undefined) ?? null,
      batteryChargeTime:
        (building.batteryChargeTime as string | null | undefined) ?? null,
      consumptionPower:
        (building.consumptionPower as string | null | undefined) ?? null,
      chargeSource:
        (building.chargeSource as string | null | undefined) ?? "None",
      chargePower: (building.chargePower as number | null | undefined) ?? null,
    };
  }
}
