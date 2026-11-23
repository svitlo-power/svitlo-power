import { Injectable, Logger } from "@nestjs/common";
import { CronJob } from "cron";
import { ProcessingService } from "../../processing/processing.service.js";

/**
 * Safety-net reconciliation job.
 *
 * `@nestjs/schedule` is in-process, so every replica triggers this job; the
 * Redis lease inside `ProcessingService` guarantees only one replica actually
 * builds and publishes.
 */
@Injectable()
export class SnapshotReconciliationJob {
  private readonly logger = new Logger(SnapshotReconciliationJob.name);
  private running = false;

  constructor(private readonly processing: ProcessingService) {}

  /** Builds the cron job that drives the reconciliation interval. */
  schedule(
    intervalMs: number,
    run: (reason: string) => Promise<void>,
  ): CronJob {
    return new CronJob(`*/${Math.floor(intervalMs / 1000)} * * * *`, () => {
      void run("scheduled");
    });
  }

  /**
   * Runs one reconciliation, recording duration and outcome.
   *
   * Errors propagate: the scheduler records the `result="error"` outcome and
   * logs them, so swallowing them here would hide failed builds.
   */
  async run(reason: string): Promise<void> {
    const result = await this.processing.reconcile(reason);
    this.logger.log(
      `Reconciliation job finished: built=${result.built} published=${result.published}`,
    );
  }

  /** Guards against overlapping executions of the same named job. */
  get isRunning(): boolean {
    return this.running;
  }

  private async runExclusive(reason: string): Promise<void> {
    if (this.running) {
      this.logger.warn(`Skipping ${reason} reconciliation: already running`);
      return;
    }
    this.running = true;
    try {
      await this.run(reason);
    } catch (error) {
      this.logger.error(
        `Reconciliation job failed: ${(error as Error).message}`,
      );
    } finally {
      this.running = false;
    }
  }
}
