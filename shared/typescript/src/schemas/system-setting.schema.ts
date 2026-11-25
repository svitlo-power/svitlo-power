import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/** Generic key/value application setting (`system_settings` collection). */
@Schema({ collection: "system_settings", versionKey: false, strict: false })
export class SystemSettingSchemaClass {
  key!: string;
  label!: Record<string, string>;
  description!: Record<string, string>;
  setting_type!:
    | "number"
    | "text"
    | "datetime"
    | "timestamp"
    | "boolean"
    | "select"
    | "localizable_text";
  default_value: unknown;
  value?: unknown;
  validation?: Record<string, unknown> | null;
  editable!: boolean;
  category_id?: unknown | null;
  created_at?: Date;
  updated_at?: Date;
}

export const SystemSettingSchema = SchemaFactory.createForClass(
  SystemSettingSchemaClass,
);

SystemSettingSchema.index({ key: 1 }, { unique: true });

export type SystemSettingDocument = HydratedDocument<SystemSettingSchemaClass>;
