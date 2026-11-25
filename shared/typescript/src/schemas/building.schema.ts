import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/**
 * Building document (`buildings` collection).
 *
 * `station` and `report_users` hold Beanie `Link` values, which serialise to
 * either a bare ObjectId or a `{ "$ref": ..., "$id": ... }` DBRef-like object.
 * Both shapes are accepted and normalised by the repository layer.
 */
@Schema({ collection: "buildings", versionKey: false, strict: false })
export class BuildingSchemaClass {
  name!: Record<string, string>;
  color!: string;
  enabled!: boolean;
  station: unknown | null;
  report_users!: unknown[];
  order!: number;
}

export const BuildingSchema = SchemaFactory.createForClass(BuildingSchemaClass);

BuildingSchema.index({ order: 1 });
BuildingSchema.index({ enabled: 1, order: 1 });

export type BuildingDocument = HydratedDocument<BuildingSchemaClass>;
