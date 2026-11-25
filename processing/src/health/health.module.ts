import { Module } from "@nestjs/common";
import { DatabaseModule } from "../database/database.module.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { ProcessingModule } from "../processing/processing.module.js";
import { HealthController } from "./health.controller.js";
import { HealthService } from "./health.service.js";

@Module({
  imports: [DatabaseModule, RedisModule, ProcessingModule],
  controllers: [HealthController],
  providers: [HealthService],
})
export class HealthModule {}
