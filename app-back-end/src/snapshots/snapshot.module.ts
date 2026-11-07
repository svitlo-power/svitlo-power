import { Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { DashboardSnapshotClient } from "../../../shared/typescript/src/index.js";
import { appConfig } from "../config/app.config.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { REDIS_READER, REDIS_SUBSCRIBER, SNAPSHOT_CLIENT } from "../tokens.js";
import { RedisClientType } from "redis";
import { SnapshotService } from "./snapshot.service.js";

@Module({
  imports: [RedisModule],
  providers: [
    {
      provide: SNAPSHOT_CLIENT,
      inject: [REDIS_READER, REDIS_SUBSCRIBER, appConfig.KEY],
      useFactory: (
        reader: RedisClientType,
        subscriber: RedisClientType,
        config: ConfigType<typeof appConfig>,
      ) =>
        new DashboardSnapshotClient(
          reader,
          subscriber,
          config.snapshotRefreshUrl,
          config.snapshotStaleThresholdSeconds,
        ),
    },
    SnapshotService,
  ],
  exports: [SnapshotService],
})
export class SnapshotModule {}
