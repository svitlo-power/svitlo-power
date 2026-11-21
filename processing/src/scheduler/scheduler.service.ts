import {
  Inject,
  Injectable,
  Logger,
  OnApplicationBootstrap,
} from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { Cron, CronExpression } from "@nestjs/schedule";
import { processingConfig } from "../config/processing.config.js";
import { MetricsService } from "../metrics/metrics.service.js";
import { SnapshotReconciliationJob } from "./jobs/snapshot-reconciliation.job.js";

/**
 * Owns the recurring reconciliation schedule.
 *
 * The job body is deliberately thin: it delegates to `ProcessingService`, which
 * holds the Redis lease that makes the work single-writer across replicas.
 */
@Injectable()
export class SchedulerService implements OnApplicationBootstrap {
  private readonly logger = new Logger(SchedulerService.name);
  private running = false;

  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    private readonly job: SnapshotReconciliationJob,
    private readonly metrics: MetricsService,
  ) {}

  onApplicationBootstrap(): void {
    if (!this.config.shadowModeEnabled) {
      this.logger.log("Scheduler disabled: shadow mode is off");
    }
  }

  /** Every five minutes, as a safety net for missed triggers. */
  @Cron(CronExpression.EVERY_5_MINUTES, { name: "snapshot-reconciliation" })
  async handleCron(): Promise<void> {
    await this.runExclusive("scheduled");
  }

  /**
   * Runs `body` unless a previous invocation is still in flight, so a slow
   * build never overlaps with the next tick.
   */
  async runExclusive(reason: string): Promise<void> {
    if (this.running) {
      this.logger.warn(`Skipping ${reason} reconciliation: already running`);
      return;
    }
    this.running = true;
    const startedAt = Date.now();
    try {
      await this.job.run(reason);
      this.metrics.jobExecution(
        "snapshot-reconciliation",
        "ok",
        (Date.now() - startedAt) / 1000,
      );
    } catch (error) {
      this.metrics.jobExecution(
        "snapshot-reconciliation",
        "error",
        (Date.now() - startedAt) / 1000,
      );
      this.logger.error(
        `Scheduled reconciliation failed: ${(error as Error).message}`,
      );
    } finally {
      this.running = false;
    }
  }
}
