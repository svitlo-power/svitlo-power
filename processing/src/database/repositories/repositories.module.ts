import { Module } from "@nestjs/common";
import { DatabaseModule } from "../database.module.js";
import { RedisModule } from "../../infrastructure/redis/redis.module.js";
import { DashboardRepository } from "./dashboard.repository.js";
import { OutagesScheduleRepository } from "./outages-schedule.repository.js";
import { SettingsRepository } from "./settings.repository.js";
import { StationsDataRepository } from "./stations-data.repository.js";

@Module({
  imports: [DatabaseModule, RedisModule],
  providers: [
    DashboardRepository,
    StationsDataRepository,
    SettingsRepository,
    OutagesScheduleRepository,
  ],
  exports: [
    DashboardRepository,
    StationsDataRepository,
    SettingsRepository,
    OutagesScheduleRepository,
  ],
})
export class RepositoriesModule {}
