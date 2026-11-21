import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/**
 * Cached Yasno outage schedule (`outages_schedule` collection).
 *
 * The legacy producer reads schedules from the Redis `outages_schedule` hash;
 * this model exists so the same collection can be read directly when Redis is
 * unavailable, and so future Processing jobs can refresh it.
 */
@Schema({ collection: "outages_schedule", versionKey: false, strict: false })
export class OutagesScheduleSchemaClass {
  queue!: string;
  data!: Record<string, unknown>;
  updated_at!: Date;
}

export const OutagesScheduleSchema = SchemaFactory.createForClass(
  OutagesScheduleSchemaClass,
);

OutagesScheduleSchema.index({ queue: 1 }, { unique: true });

export type OutagesScheduleDocument =
  HydratedDocument<OutagesScheduleSchemaClass>;
