import {
  Inject,
  Injectable,
  Logger,
  OnApplicationBootstrap,
  OnModuleDestroy,
} from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { processingConfig } from "../config/processing.config.js";
import { MetricsService } from "../metrics/metrics.service.js";
import { SnapshotReconciliationJob } from "./jobs/snapshot-reconciliation.job.js";

export const RECONCILIATION_JOB_NAME = "snapshot-reconciliation";

/**
 * Owns the recurring reconciliation schedule.
 *
 * The job body is deliberately thin: it delegates to `ProcessingService`, which
 * holds the Redis lease that makes the work single-writer across replicas.
 */
@Injectable()
export class SchedulerService
  implements OnApplicationBootstrap, OnModuleDestroy
{
  private readonly logger = new Logger(SchedulerService.name);
  private timer: NodeJS.Timeout | null = null;

  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    private readonly job: SnapshotReconciliationJob,
    private readonly metrics: MetricsService,
  ) {}

  onApplicationBootstrap(): void {
    if (!this.config.shadowModeEnabled) {
      this.logger.log("Scheduler disabled: shadow mode is off");
      return;
    }
    // Registered from the configured interval so
    // PROCESSING_RECONCILIATION_INTERVAL_SECONDS is actually honoured.
    this.timer = this.job.schedule(
      this.config.reconciliationIntervalMs,
      (reason) => this.runExclusive(reason),
    );
    this.logger.log(
      `Snapshot reconciliation scheduled every ${this.config.reconciliationIntervalMs / 1000}s`,
    );
  }

  onModuleDestroy(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  /**
   * Runs `body` unless a previous invocation is still in flight, so a slow
   * build never overlaps with the next tick.
   */
  async runExclusive(reason: string): Promise<void> {
    if (this.job.isRunning) {
      this.logger.warn(`Skipping ${reason} reconciliation: already running`);
      return;
    }
    const startedAt = Date.now();
    try {
      await this.job.run(reason);
      this.metrics.jobExecution(
        RECONCILIATION_JOB_NAME,
        "ok",
        (Date.now() - startedAt) / 1000,
      );
    } catch (error) {
      this.metrics.jobExecution(
        RECONCILIATION_JOB_NAME,
        "error",
        (Date.now() - startedAt) / 1000,
      );
      this.logger.error(
        `Scheduled reconciliation failed: ${(error as Error).message}`,
      );
    }
  }
}
