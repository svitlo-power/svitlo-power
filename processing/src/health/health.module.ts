import { Module } from "@nestjs/common";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { ProcessingModule } from "../processing/processing.module.js";
import { HealthController } from "./health.controller.js";
import { HealthService } from "./health.service.js";

@Module({
  imports: [RedisModule, ProcessingModule],
  controllers: [HealthController],
  providers: [HealthService],
})
export class HealthModule {}
