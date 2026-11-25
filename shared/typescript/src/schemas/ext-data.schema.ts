import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/** Reporter observation document (`ext_data` collection, time series). */
@Schema({ collection: "ext_data", versionKey: false, strict: false })
export class ExtDataSchemaClass {
  user_id: unknown;
  grid_state!: boolean;
  received_at!: Date;
}

export const ExtDataSchema = SchemaFactory.createForClass(ExtDataSchemaClass);

ExtDataSchema.index({ user_id: 1, received_at: -1 });

export type ExtDataDocument = HydratedDocument<ExtDataSchemaClass>;
