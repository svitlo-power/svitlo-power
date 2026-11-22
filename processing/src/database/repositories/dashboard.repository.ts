import { Injectable } from "@nestjs/common";
import { InjectModel } from "@nestjs/mongoose";
import { isObjectId } from "@svitlo-power/shared-typescript";
import {
  BuildingDocument,
  BuildingSchemaClass,
  StationDocument,
  StationSchemaClass,
} from "@svitlo-power/shared-typescript/schemas";
import { Model, Types } from "mongoose";

export interface BuildingRecord {
  id: string;
  name: Record<string, string>;
  color: string;
  enabled: boolean;
  order: number;
  stationId: string | null;
  reportUserIds: string[];
}

export interface StationRecord {
  id: string;
  connectionStatus: string | null;
  batteryCapacity: number | null;
  dischargeTargetSoc: number | null;
  chargeTargetSoc: number | null;
}

/** `PowerEstimationStation` view of a station record. */
export function toPowerEstimationStation(station: StationRecord | null): {
  discharge_target_soc?: number | null;
  charge_target_soc?: number | null;
} | null {
  if (station === null) return null;
  return {
    discharge_target_soc: station.dischargeTargetSoc,
    charge_target_soc: station.chargeTargetSoc,
  };
}

/**
 * Extracts the ObjectId from a Beanie `Link` value.
 *
 * Beanie stores links in two shapes, and both must resolve to the referenced
 * `_id`:
 *
 * - a bare `ObjectId`
 * - a BSON `DBRef`, which the Node driver exposes as
 *   `{ collection, oid, db, fields }` — note `oid`, not `$id`
 *
 * The `$ref`/`$id` pair only appears after a `JSON.stringify` round trip, so
 * all three spellings are handled.
 */
export function resolveLinkId(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return isObjectId(value) ? value : null;
  if (value instanceof Types.ObjectId) return value.toHexString();
  if (typeof value === "object") {
    const record = value as Record<string, unknown>;
    // `oid` is the live DBRef field; `$id`/`_id`/`id` cover the serialized
    // form and hand-built references.
    const nested = record.oid ?? record.$id ?? record._id ?? record.id;
    if (nested === undefined || nested === null) return null;
    return resolveLinkId(nested);
  }
  return null;
}

/**
 * Read-only access to buildings and their bound stations.
 *
 * Mirrors `DashboardReadRepository.get_buildings` and
 * `StationsReadRepository.get_stations` from `shared/python`.
 */
@Injectable()
export class DashboardRepository {
  constructor(
    @InjectModel("Building")
    private readonly buildingModel: Model<BuildingDocument>,
    @InjectModel("Station")
    private readonly stationModel: Model<StationDocument>,
  ) {}

  /**
   * Lists buildings, enabled-only by default, ordered by `order` exactly like
   * the Python repository (`Building.find(query).sort(Building.order)`).
   */
  async getBuildings(
    ids?: string[] | null,
    all = false,
  ): Promise<BuildingRecord[]> {
    const filter: Record<string, unknown> = {};
    if (ids !== undefined && ids !== null) {
      filter._id = { $in: ids.map((id) => new Types.ObjectId(id)) };
    } else if (!all) {
      filter.enabled = true;
    }

    const documents = await this.buildingModel
      .find(filter)
      .lean<(BuildingSchemaClass & { _id: unknown })[]>()
      .sort({ order: 1 })
      .exec();

    return documents.map((document) => toBuildingRecord(document));
  }

  /** Resolves the stations referenced by the given building ids. */
  async getStationsByIds(ids: string[]): Promise<Map<string, StationRecord>> {
    const unique = [...new Set(ids.filter((id) => isObjectId(id)))];
    if (unique.length === 0) return new Map();

    const documents = await this.stationModel
      .find({ _id: { $in: unique.map((id) => new Types.ObjectId(id)) } })
      .lean<(StationSchemaClass & { _id: unknown })[]>()
      .exec();

    return new Map(
      documents.map((document) => [
        String(document._id),
        toStationRecord(document),
      ]),
    );
  }
}

function toBuildingRecord(
  document: BuildingSchemaClass & { _id: unknown },
): BuildingRecord {
  const reportUsers = Array.isArray(document.report_users)
    ? document.report_users
    : [];
  return {
    id: String(document._id),
    name: document.name ?? {},
    color: document.color,
    enabled: document.enabled,
    order: document.order,
    stationId: resolveLinkId(document.station),
    reportUserIds: reportUsers
      .map((user) => resolveLinkId(user))
      .filter((id): id is string => id !== null),
  };
}

function toStationRecord(
  document: StationSchemaClass & { _id: unknown },
): StationRecord {
  return {
    id: String(document._id),
    connectionStatus: document.connection_status ?? null,
    batteryCapacity: document.battery_capacity ?? null,
    dischargeTargetSoc: document.discharge_target_soc ?? null,
    chargeTargetSoc: document.charge_target_soc ?? null,
  };
}
