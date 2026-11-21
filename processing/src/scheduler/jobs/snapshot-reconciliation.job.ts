import { Injectable, Logger } from "@nestjs/common";
import { SchedulerRegistry } from "@nestjs/schedule";
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

  constructor(
    private readonly registry: SchedulerRegistry,
    private readonly processing: ProcessingService,
  ) {}

  /** Runs one reconciliation, recording duration and outcome. */
  async run(reason: string): Promise<void> {
    try {
      const result = await this.processing.reconcile(reason);
      this.logger.log(
        `Reconciliation job finished: built=${result.built} published=${result.published}`,
      );
    } catch (error) {
      this.logger.error(
        `Reconciliation job failed: ${(error as Error).message}`,
      );
    }
  }

  /** Guards against overlapping executions of the same named job. */
  isRunning(name: string): boolean {
    const job = this.registry.getCronJob(name) as unknown as {
      isRunning?: () => boolean;
    };
    return typeof job.isRunning === "function" ? job.isRunning() : false;
  }
}
