import { Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { RedisClientType } from "redis";
import { appConfig } from "../config/app.config.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { MetricsService } from "../metrics/metrics.service.js";
import { DashboardSnapshotClient } from "../shared.js";
import { REDIS_READER, REDIS_SUBSCRIBER, SNAPSHOT_CLIENT } from "../tokens.js";
import { SnapshotService } from "./snapshot.service.js";

@Module({
  imports: [RedisModule, MetricsModule],
  providers: [
    {
      provide: SNAPSHOT_CLIENT,
      inject: [REDIS_READER, REDIS_SUBSCRIBER, appConfig.KEY, MetricsService],
      useFactory: (
        reader: RedisClientType,
        subscriber: RedisClientType,
        config: ConfigType<typeof appConfig>,
        metrics: MetricsService,
      ) =>
        new DashboardSnapshotClient({
          reader,
          subscriber,
          refreshUrl: config.snapshotRefreshUrl,
          staleThresholdSeconds: config.snapshotStaleThresholdSeconds,
          requestedBy: "app-back-end",
          metrics,
        }),
    },
    SnapshotService,
  ],
  exports: [SnapshotService],
})
export class SnapshotModule {}
