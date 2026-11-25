import { Schema, SchemaFactory } from "@nestjs/mongoose";
import { HydratedDocument } from "mongoose";

/** Application user document (`users` collection). */
@Schema({ collection: "users", versionKey: false, strict: false })
export class UserSchemaClass {
  name!: string;
  password?: string | null;
  is_active!: boolean;
  is_reporter!: boolean;
  is_admin!: boolean;
  api_key?: string | null;
  password_reset_token?: string | null;
  reset_token_expiration?: Date | null;
  report_mode?: "ping" | "event" | null;
}

export const UserSchema = SchemaFactory.createForClass(UserSchemaClass);

UserSchema.index({ is_reporter: 1 });

export type UserDocument = HydratedDocument<UserSchemaClass>;
