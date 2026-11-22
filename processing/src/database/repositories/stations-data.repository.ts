import { Injectable } from "@nestjs/common";
import { InjectModel } from "@nestjs/mongoose";
import { isObjectId } from "@svitlo-power/shared-typescript";
import {
  ExtDataDocument,
  StationDataDocument,
  StationDataSchemaClass,
} from "@svitlo-power/shared-typescript/schemas";
import { Model, Types } from "mongoose";

export interface StationDataRecord {
  batterySoc: number | null;
  chargePower: number | null;
  dischargePower: number | null;
  generationPower: number | null;
  wirePower: number | null;
  consumptionPower: number | null;
  lastUpdateTime: Date | null;
}

export interface ExtDataRecord {
  gridState: boolean;
  receivedAt: Date;
}

/**
 * Read-only access to station measurements and reporter observations.
 *
 * Mirrors `StationsDataReadRepository` and `ExtDataReadRepository` from
 * `shared/python`, including the `$ifNull`-based average that treats missing
 * samples as zero.
 */
@Injectable()
export class StationsDataRepository {
  constructor(
    @InjectModel("StationData")
    private readonly stationDataModel: Model<StationDataDocument>,
    @InjectModel("ExtData")
    private readonly extDataModel: Model<ExtDataDocument>,
  ) {}

  /** Latest measurement for a station, or null when it has never reported. */
  async getLastStationData(
    stationId: string,
  ): Promise<StationDataRecord | null> {
    const document = await this.stationDataModel
      .findOne({ station_id: toObjectId(stationId) })
      .sort({ last_update_time: -1 })
      .lean<StationDataSchemaClass>()
      .exec();
    return document ? toStationDataRecord(document) : null;
  }

  /**
   * Average of a numeric column over the window, treating missing values as 0
   * (`$avg: { $ifNull: ["$column", 0] }`). Returns 0 when there are no samples.
   */
  async getAverageColumn(
    stationId: string,
    column:
      | "consumption_power"
      | "charge_power"
      | "discharge_power"
      | "generation_power"
      | "grid_power"
      | "wire_power",
    start: Date | null,
    end: Date | null,
  ): Promise<number> {
    const match: Record<string, unknown> = {
      station_id: toObjectId(stationId),
    };
    if (start || end) {
      const range: Record<string, Date> = {};
      if (start) range.$gte = start;
      if (end) range.$lte = end;
      if (Object.keys(range).length > 0) match.last_update_time = range;
    }

    const [result] = await this.stationDataModel
      .aggregate<{ avgValue: number | null }>([
        { $match: match },
        {
          $group: {
            _id: null,
            avgValue: { $avg: { $ifNull: [`$${column}`, 0] } },
          },
        },
      ])
      .exec();

    if (!result || result.avgValue === null || result.avgValue === undefined) {
      return 0;
    }
    return Number(result.avgValue);
  }

  /**
   * Latest observation per reporter user. Users without observations are
   * omitted, matching the Python `first_or_none` per-user lookups.
   */
  async getLastExtDataByUserIds(
    userIds: string[],
  ): Promise<Map<string, ExtDataRecord>> {
    const unique = [...new Set(userIds.filter((id) => isObjectId(id)))];
    if (unique.length === 0) return new Map();

    const documents = await this.extDataModel
      .aggregate<
        Record<string, unknown> & {
          _id: Types.ObjectId;
          gridState: boolean;
          receivedAt: Date;
        }
      >([
        {
          $match: {
            user_id: { $in: unique.map((id) => new Types.ObjectId(id)) },
          },
        },
        { $sort: { received_at: -1 } },
        {
          $group: {
            _id: "$user_id",
            gridState: { $first: "$grid_state" },
            receivedAt: { $first: "$received_at" },
          },
        },
      ])
      .exec();

    return new Map(
      documents.map((document) => [
        String(document._id),
        { gridState: document.gridState, receivedAt: document.receivedAt },
      ]),
    );
  }

  /**
   * Whether a station should be treated as offline because its newest sample is
   * older than `reportIntervalSeconds * assumedOfflineReports`.
   */
  async getAssumedConnectionStatus(
    stationId: string,
    reportIntervalSeconds: number,
    assumedOfflineReports: number,
  ): Promise<"NORMAL" | "OFFLINE"> {
    const latest = await this.stationDataModel
      .findOne({ station_id: toObjectId(stationId) })
      .sort({ last_update_time: -1 })
      .lean<StationDataSchemaClass>()
      .exec();
    if (!latest || !latest.last_update_time) return "OFFLINE";

    const lastUpdate = new Date(latest.last_update_time).getTime();
    const elapsedSeconds = (Date.now() - lastUpdate) / 1000;
    const threshold = reportIntervalSeconds * assumedOfflineReports;
    return elapsedSeconds > threshold ? "OFFLINE" : "NORMAL";
  }
}

function toStationDataRecord(
  document: StationDataSchemaClass,
): StationDataRecord {
  return {
    batterySoc: document.battery_soc ?? null,
    chargePower: document.charge_power ?? null,
    dischargePower: document.discharge_power ?? null,
    generationPower: document.generation_power ?? null,
    wirePower: document.wire_power ?? null,
    consumptionPower: document.consumption_power ?? null,
    lastUpdateTime: document.last_update_time ?? null,
  };
}

function toObjectId(value: string): Types.ObjectId | string {
  return isObjectId(value) ? new Types.ObjectId(value) : value;
}
