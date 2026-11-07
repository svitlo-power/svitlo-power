import { Module } from "@nestjs/common";
import { InternalApiModule } from "../infrastructure/internal-api/internal-api.module.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { SnapshotModule } from "../snapshots/snapshot.module.js";
import { HealthController } from "./health.controller.js";
import { HealthService } from "./health.service.js";

@Module({
  imports: [InternalApiModule, RedisModule, SnapshotModule],
  controllers: [HealthController],
  providers: [HealthService],
})
export class HealthModule {}
