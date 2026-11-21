import { Module } from "@nestjs/common";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { LeaseModule } from "../lease/lease.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { ShadowComparator } from "./shadow-comparator.service.js";
import { ShadowPublisher } from "./shadow-publisher.service.js";

@Module({
  imports: [RedisModule, LeaseModule, MetricsModule],
  providers: [ShadowPublisher, ShadowComparator],
  exports: [ShadowPublisher, ShadowComparator],
})
export class ShadowModule {}
