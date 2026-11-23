import {
  Inject,
  Injectable,
  Logger,
  OnApplicationBootstrap,
  OnModuleDestroy,
} from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import {
  DashboardSnapshot,
  SnapshotSection,
  changedSections,
} from "../shared.js";
import { processingConfig } from "../config/processing.config.js";
import { PROCESSING_LEASE } from "../tokens.js";
import { ProcessingLease } from "../lease/processing-lease.service.js";
import { MetricsService } from "../metrics/metrics.service.js";
import { ShadowComparator } from "../shadow/shadow-comparator.service.js";
import { ShadowPublisher } from "../shadow/shadow-publisher.service.js";
import { SnapshotBuilder } from "../snapshot/snapshot.builder.js";
import { SnapshotValidator } from "../snapshot/snapshot.validator.js";

export interface ReconcileResult {
  built: boolean;
  published: boolean;
  epoch: number;
  version: number;
  changed: SnapshotSection[];
  parity: number | null;
  mismatches: number;
  reason?: string;
}

/**
 * Coordinates the shadow snapshot flow: build, validate, publish to the shadow
 * namespace, then compare with the legacy producer.
 *
 * Only the lease holder performs singleton work, so multiple replicas cannot
 * perform conflicting builds.
 */
@Injectable()
export class ProcessingService
  implements OnApplicationBootstrap, OnModuleDestroy
{
  private readonly logger = new Logger(ProcessingService.name);
  private epoch = 0;
  private lastSnapshot: DashboardSnapshot | null = null;
  private inFlight: Promise<ReconcileResult> | null = null;
  private lastResult: ReconcileResult | null = null;
  private startedAt = Date.now();

  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    @Inject(PROCESSING_LEASE) private readonly lease: ProcessingLease,
    private readonly builder: SnapshotBuilder,
    private readonly validator: SnapshotValidator,
    private readonly publisher: ShadowPublisher,
    private readonly comparator: ShadowComparator,
    private readonly metrics: MetricsService,
  ) {}

  async onApplicationBootstrap(): Promise<void> {
    if (!this.config.shadowModeEnabled) {
      this.logger.log("Shadow mode disabled; snapshot reconciliation is idle");
      return;
    }
    this.startedAt = Date.now();
    await this.lease.acquire();
    this.lease.start();
    try {
      await this.reconcile("startup");
    } catch (error) {
      // A failed first build must not stop the container from booting: the
      // scheduler and the refresh trigger retry, and /health/ready reports it.
      this.logger.error(
        `Startup reconciliation failed: ${(error as Error).message}`,
      );
      this.metrics.writeError("exception");
      this.lastResult = {
        built: false,
        published: false,
        epoch: this.epoch,
        version: 0,
        changed: [],
        parity: null,
        mismatches: 0,
        reason: "exception",
      };
    }
  }

  async onModuleDestroy(): Promise<void> {
    await this.lease.release();
  }

  isEnabled(): boolean {
    return this.config.shadowModeEnabled;
  }

  /**
   * Builds, publishes and compares one snapshot.
   *
   * Concurrent callers share the in-flight build, which coalesces bursts of
   * triggers into a single reconciliation.
   */
  async reconcile(reason: string): Promise<ReconcileResult> {
    if (!this.config.shadowModeEnabled) {
      return {
        built: false,
        published: false,
        epoch: 0,
        version: 0,
        changed: [],
        parity: null,
        mismatches: 0,
        reason: "disabled",
      };
    }
    this.metrics.refreshRequest(reason);
    if (this.inFlight) {
      this.metrics.refreshCoalescedCount();
      return this.inFlight;
    }
    const run = this.runReconcile(reason).finally(() => {
      this.inFlight = null;
    });
    this.inFlight = run;
    return run;
  }

  private async runReconcile(reason: string): Promise<ReconcileResult> {
    if (!this.lease.isHolder && !(await this.lease.acquire())) {
      this.logger.warn("Skipping reconciliation: shadow lease not held");
      return {
        built: false,
        published: false,
        epoch: this.epoch,
        version: 0,
        changed: [],
        parity: null,
        mismatches: 0,
        reason: "no-lease",
      };
    }

    if (this.epoch === 0) {
      this.epoch = await this.publisher.initialiseVersionKeys(this.startedAt);
    }
    const version = await this.publisher.nextVersion();

    const { snapshot, timing } = await this.builder.build({
      epoch: this.epoch,
      version,
    });
    this.metrics.observeBuildDuration(timing.durationSeconds);

    const validation = this.validator.validate(snapshot);
    if (!validation.valid) {
      this.logger.error(
        `Snapshot failed validation: ${validation.errors.join("; ")}`,
      );
      this.metrics.writeError("validation");
      return {
        built: false,
        published: false,
        epoch: snapshot.epoch,
        version: snapshot.version,
        changed: [],
        parity: null,
        mismatches: 0,
        reason: "validation",
      };
    }

    const changed = changedSections(this.lastSnapshot, snapshot);
    const publish = await this.publisher.publish(snapshot);
    if (publish.published) {
      this.lastSnapshot = snapshot;
      this.metrics.setSnapshotState(
        snapshot.epoch,
        snapshot.version,
        Math.max(0, (Date.now() - Date.parse(snapshot.generatedAt)) / 1000),
      );
    }

    const comparison = await this.comparator.compareWithProduction(snapshot);
    const result: ReconcileResult = {
      built: true,
      published: publish.published,
      epoch: snapshot.epoch,
      version: snapshot.version,
      changed,
      parity: comparison.compared ? comparison.parity : null,
      mismatches: comparison.mismatches,
      reason: publish.published ? undefined : publish.reason,
    };
    this.lastResult = result;
    this.logger.log(
      `Shadow reconciliation (${reason}): version=${snapshot.version} changed=[${changed.join(",")}] parity=${result.parity === null ? "n/a" : result.parity.toFixed(4)}`,
    );
    return result;
  }

  /** Health/metrics view of the most recent reconciliation. */
  status(): "healthy" | "unhealthy" {
    if (!this.config.shadowModeEnabled) return "healthy";
    if (this.lastResult === null)
      return this.epoch === 0 ? "unhealthy" : "healthy";
    return this.lastResult.built ? "healthy" : "unhealthy";
  }

  details() {
    return {
      shadow_mode: this.config.shadowModeEnabled,
      lease_held: this.lease.isHolder,
      epoch: this.epoch,
      version: this.lastSnapshot?.version ?? 0,
      age_seconds: this.lastSnapshot
        ? Math.max(
            0,
            (Date.now() - Date.parse(this.lastSnapshot.generatedAt)) / 1000,
          )
        : null,
      last_build_at: this.lastResult ? new Date().toISOString() : null,
      parity: this.lastResult?.parity ?? null,
      changed_sections: this.lastResult?.changed ?? [],
    };
  }
}
