import { Logger, Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { randomUUID } from "node:crypto";
import { RedisClientType } from "redis";
import { processingConfig } from "../config/processing.config.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { MetricsService } from "../metrics/metrics.service.js";
import { LEASE_KEY, SHADOW_LEASE_KEY } from "../shared.js";
import { PROCESSING_LEASE, REDIS_WRITER } from "../tokens.js";
import { ProcessingLease } from "./processing-lease.service.js";

/**
 * Chooses the lease namespace for the configured mode.
 *
 * The key must match the namespace the instance writes to: the Lua write script
 * fences on the production lease key, so holding the shadow one after the
 * cutover would reject every publish as `lease-lost` while the instance still
 * reports `lease_held`.
 */
export function leaseKeyFor(publishEnabled: boolean): string {
  return publishEnabled ? LEASE_KEY : SHADOW_LEASE_KEY;
}

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
            key: leaseKeyFor(config.publishEnabled),
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
