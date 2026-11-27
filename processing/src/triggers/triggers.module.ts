import { Module } from "@nestjs/common";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { ProcessingModule } from "../processing/processing.module.js";
import { RefreshController } from "./refresh.controller.js";
import { RefreshCoordinator } from "./refresh-coordinator.service.js";
import { SnapshotRefreshSubscriber } from "./snapshot-refresh.subscriber.js";

@Module({
  imports: [ProcessingModule, RedisModule, MetricsModule],
  controllers: [RefreshController],
  providers: [RefreshCoordinator, SnapshotRefreshSubscriber],
  exports: [RefreshCoordinator],
})
export class TriggersModule {}
