import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/**
 * Station measurement document (`station_data` collection, time series).
 *
 * `station_id` references `stations._id`, matching the Python
 * `StationData.station_id: PydanticObjectId` field.
 */
@Schema({ collection: "station_data", versionKey: false, strict: false })
export class StationDataSchemaClass {
  station_id: unknown;
  battery_power?: number | null;
  battery_soc?: number | null;
  charge_power?: number | null;
  code?: string | null;
  consumption_power?: number | null;
  discharge_power?: number | null;
  generation_power?: number | null;
  grid_power?: number | null;
  irradiate_intensity?: number | null;
  last_update_time?: Date | null;
  msg?: string | null;
  purchase_power?: number | null;
  request_id?: string | null;
  wire_power?: number | null;
}

export const StationDataSchema = SchemaFactory.createForClass(
  StationDataSchemaClass,
);

StationDataSchema.index({ station_id: 1, last_update_time: -1 });
StationDataSchema.index({ last_update_time: -1 });

export type StationDataDocument = HydratedDocument<StationDataSchemaClass>;
