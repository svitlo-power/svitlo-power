import { Module } from "@nestjs/common";
import { DatabaseModule } from "../database/database.module.js";
import { RedisModule } from "../infrastructure/redis/redis.module.js";
import { LeaseModule } from "../lease/lease.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { RepositoriesModule } from "../database/repositories/repositories.module.js";
import { SnapshotBuilder } from "./snapshot.builder.js";
import { SnapshotPublisher } from "./snapshot-publisher.service.js";
import { SnapshotValidator } from "./snapshot.validator.js";

@Module({
  imports: [
    DatabaseModule,
    RepositoriesModule,
    RedisModule,
    LeaseModule,
    MetricsModule,
  ],
  providers: [SnapshotBuilder, SnapshotValidator, SnapshotPublisher],
  exports: [SnapshotBuilder, SnapshotValidator, SnapshotPublisher],
})
export class SnapshotModule {}
