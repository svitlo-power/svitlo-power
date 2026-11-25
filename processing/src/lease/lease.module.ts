import { Logger, Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { randomUUID } from "node:crypto";
import { RedisClientType } from "redis";
import { processingConfig } from "../config/processing.config.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { MetricsService } from "../metrics/metrics.service.js";
import { SHADOW_LEASE_KEY } from "../shared.js";
import { PROCESSING_LEASE, REDIS_WRITER } from "../tokens.js";
import { ProcessingLease } from "./processing-lease.service.js";

@Module({
  imports: [RedisModule, MetricsModule],
  providers: [
    {
      provide: PROCESSING_LEASE,
      inject: [REDIS_WRITER, processingConfig.KEY, MetricsService],
      useFactory: (
        redis: RedisClientType,
        config: ConfigType<typeof processingConfig>,
        metrics: MetricsService,
      ) => {
        const logger = new Logger("ProcessingLease");
        const instanceId = `processing-${process.pid}-${randomUUID().slice(0, 8)}`;
        return new ProcessingLease(
          redis,
          {
            key: SHADOW_LEASE_KEY,
            instanceId,
            ttlSeconds: config.leaseTtlSeconds,
            renewIntervalSeconds: config.leaseRenewIntervalSeconds,
            onAcquired: () => {
              metrics.leaseAcquisition();
            },
            onLost: () => {
              logger.warn(`Shadow lease lost by ${instanceId}`);
              metrics.leaseLoss();
            },
          },
          metrics,
        );
      },
    },
  ],
  exports: [PROCESSING_LEASE],
})
export class LeaseModule {}
