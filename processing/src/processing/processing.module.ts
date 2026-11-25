import { Module } from "@nestjs/common";
import { LeaseModule } from "../lease/lease.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { ShadowModule } from "../shadow/shadow.module.js";
import { SnapshotModule } from "../snapshot/snapshot.module.js";
import { ProcessingService } from "./processing.service.js";

@Module({
  imports: [LeaseModule, MetricsModule, ShadowModule, SnapshotModule],
  providers: [ProcessingService],
  exports: [ProcessingService],
})
export class ProcessingModule {}
