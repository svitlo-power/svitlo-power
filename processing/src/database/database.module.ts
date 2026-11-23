import { Module } from "@nestjs/common";
import { ConfigModule, ConfigType } from "@nestjs/config";
import { MongooseModule } from "@nestjs/mongoose";
import {
  BuildingSchema,
  ExtDataSchema,
  OutagesScheduleSchema,
  StationDataSchema,
  StationSchema,
  SystemSettingSchema,
  UserSchema,
} from "@svitlo-power/shared-typescript/schemas";
import { processingConfig } from "../config/processing.config.js";

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
        // The collections belong to the Python/Beanie back-end. Building the
        // indexes declared on the shared schemas would write to production
        // during the shadow phase (and can fail on duplicate keys), so index
        // management stays with the owner service.
        autoIndex: false,
        autoCreate: false,
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
