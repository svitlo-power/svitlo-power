import { Module } from "@nestjs/common";
import { ScheduleModule } from "@nestjs/schedule";
import { MetricsModule } from "../metrics/metrics.module.js";
import { ProcessingModule } from "../processing/processing.module.js";
import { SnapshotReconciliationJob } from "./jobs/snapshot-reconciliation.job.js";
import { SchedulerService } from "./scheduler.service.js";

@Module({
  imports: [ScheduleModule.forRoot(), MetricsModule, ProcessingModule],
  providers: [SnapshotReconciliationJob, SchedulerService],
  exports: [SchedulerService],
})
export class SchedulerModule {}
