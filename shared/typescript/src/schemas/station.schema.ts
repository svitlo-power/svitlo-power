import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/** Station document (`stations` collection). */
@Schema({ collection: "stations", versionKey: false, strict: false })
export class StationSchemaClass {
  station_id?: number | null;
  station_name?: string | null;
  station_alias?: Record<string, string> | null;

  location_lat?: number | null;
  location_lng?: number | null;
  location_address?: string | null;

  region_nation_id?: number | null;
  region_timezone?: string | null;

  grid_interconnection_type?: string | null;
  installed_capacity?: number | null;

  start_operating_time?: Date | null;
  created_date?: Date | null;
  last_update_time?: Date | null;

  connection_status?: string | null;
  contact_phone?: string | null;
  owner_name?: string | null;

  generation_power?: number | null;
  battery_capacity?: number | null;

  discharge_target_soc?: number | null;
  charge_target_soc?: number | null;

  order!: number;
  enabled!: boolean;

  connection_id?: unknown | null;
}

export const StationSchema = SchemaFactory.createForClass(StationSchemaClass);

StationSchema.index({ order: 1 });
StationSchema.index({ enabled: 1, order: 1 });
StationSchema.index({ station_id: 1 });

export type StationDocument = HydratedDocument<StationSchemaClass>;
