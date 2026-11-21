import { Module } from "@nestjs/common";
import { ConfigModule, ConfigType } from "@nestjs/config";
import { MongooseModule } from "@nestjs/mongoose";
import { processingConfig } from "../config/processing.config.js";
import {
  BuildingSchema,
  ExtDataSchema,
  OutagesScheduleSchema,
  StationDataSchema,
  StationSchema,
  SystemSettingSchema,
  UserSchema,
} from "../shared.js";

/**
 * Registers the Mongoose connection and every schema the snapshot builder
 * reads. Schemas live in `@svitlo-power/shared-typescript` so future services
 * share one definition of the Mongo documents.
 */
@Module({
  imports: [
    MongooseModule.forRootAsync({
      imports: [ConfigModule],
      inject: [processingConfig.KEY],
      useFactory: (config: ConfigType<typeof processingConfig>) => ({
        uri: config.mongoUri,
        dbName: config.mongoDatabase,
      }),
    }),
    MongooseModule.forFeature([
      { name: "Building", schema: BuildingSchema },
      { name: "Station", schema: StationSchema },
      { name: "StationData", schema: StationDataSchema },
      { name: "ExtData", schema: ExtDataSchema },
      { name: "User", schema: UserSchema },
      { name: "SystemSetting", schema: SystemSettingSchema },
      { name: "OutagesSchedule", schema: OutagesScheduleSchema },
    ]),
  ],
  exports: [MongooseModule],
})
export class DatabaseModule {}
