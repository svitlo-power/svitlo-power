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
  /** True when this caller's request was folded into an earlier build. */
  coalesced: boolean;
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
  private lastBuildAt: number | null = null;
  /**
   * Shared promise for the follow-up build that a mid-build request waits on.
   *
   * A single `resolve` slot would be overwritten by every caller that arrives
   * during the same build, so all but the last would wait forever — and if the
   * stuck waiter is the `RefreshCoordinator`, its `pending` never clears and
   * every later `POST /internal/v1/snapshots/refresh` hangs with it.
   */
  private followUp: {
    promise: Promise<ReconcileResult>;
    resolve: (result: ReconcileResult) => void;
    reject: (error: Error) => void;
  } | null = null;
  /**
   * Set in `onModuleDestroy`, which Nest runs *before* the Redis clients are
   * closed and before the HTTP server stops accepting requests.
   *
   * `onApplicationShutdown` runs last — after the lease is released and both
   * Redis clients have `quit()` — so rejecting waiters there would race the
   * in-flight build's `finally`, which would then start a follow-up against
   * closed connections and answer the waiters with a Redis error instead of the
   * shutdown reason.
   */
  private shuttingDown = false;
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
  ) {
    // The epoch is cached per process, so it has to be re-seeded whenever the
    // lease is (re)acquired: another replica may have written a newer epoch
    // while this one was a standby, and every publish would then be rejected
    // as `epoch-stale` until a restart.
    this.lease.onAcquired(() => {
      this.epoch = 0;
    });
  }

  async onApplicationBootstrap(): Promise<void> {
    if (!this.config.shadowModeEnabled) {
      this.logger.log("Shadow mode disabled; snapshot reconciliation is idle");
      return;
    }
    this.startedAt = Date.now();
    try {
      // A transient Redis error during `SET NX` must not fail the bootstrap
      // either: the scheduler retries and /health/ready reports the state.
      await this.lease.acquire();
      this.lease.start();
    } catch (error) {
      this.recordFailure("startup", error as Error);
      return;
    }
    // The first build is deliberately *not* awaited here: `onApplicationBootstrap`
    // runs before the HTTP server binds, so a slow Mongo would leave
    // /health/live unreachable for the whole build. The scheduler owns the
    // recurring cadence and /health/ready reports the outcome.
    void this.reconcile("startup").catch(() => undefined);
  }

  async onModuleDestroy(): Promise<void> {
    // Reject before the lease is released and before Redis closes, so waiters
    // learn the real reason instead of a connection error from the follow-up
    // build the `finally` would otherwise start.
    this.shuttingDown = true;
    this.followUp?.reject(new Error("processing is shutting down"));
    this.followUp = null;
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
        coalesced: false,
        reason: "disabled",
      };
    }
    this.metrics.refreshRequest(reason);
    if (this.shuttingDown) {
      // The HTTP server is still accepting requests while the modules are being
      // destroyed; failing fast beats starting a build against closing
      // connections.
      throw new Error("processing is shutting down");
    }
    if (this.inFlight) {
      this.metrics.refreshCoalescedCount();
      // A request that arrives mid-build would otherwise be answered with the
      // snapshot from *before* the current build. Await a follow-up build that
      // starts once the current one settles, so the caller cannot be told
      // `accepted` with a version that predates its own change.
      return this.waitForFollowUp();
    }
    const run = this.runReconcile(reason)
      .catch((error: Error) => {
        // Every failure path, not just startup, has to reach health and the
        // write-error metric; otherwise a broken build looks like a healthy
        // service until the next successful one.
        this.recordFailure(reason, error);
        throw error;
      })
      .finally(() => {
        this.inFlight = null;
        const followUp = this.followUp;
        if (!followUp) return;
        this.followUp = null;
        if (this.shuttingDown) {
          // The process is going away: a follow-up would run against Redis
          // connections that are already closing.
          followUp.reject(new Error("processing is shutting down"));
          return;
        }
        // Every waiter shares this one promise, so a failing follow-up rejects
        // all of them instead of leaving the rest pending.
        void this.reconcile("follow-up").then(
          followUp.resolve,
          followUp.reject,
        );
      });
    this.inFlight = run;
    return run;
  }

  /** Resolves once the current build (if any) has settled. Used by tests. */
  async inFlightSettled(): Promise<void> {
    await this.inFlight;
  }

  /** Records a failed reconciliation so health stops reporting the last success. */
  private recordFailure(reason: string, error: Error): void {
    this.logger.error(`Reconciliation (${reason}) failed: ${error.message}`);
    this.metrics.writeError("exception");
    this.lastResult = {
      built: false,
      published: false,
      epoch: this.epoch,
      version: 0,
      changed: [],
      parity: null,
      mismatches: 0,
      coalesced: false,
      reason: "exception",
    };
  }

  /**
   * Resolves with the follow-up build that the in-flight build schedules for
   * requests arriving mid-build.
   *
   * The promise is created once per in-flight build and shared by every caller,
   * so no waiter can be starved by a later one overwriting a resolver slot.
   */
  private waitForFollowUp(): Promise<ReconcileResult> {
    if (this.followUp) return this.followUp.promise;
    let resolve!: (result: ReconcileResult) => void;
    let reject!: (error: Error) => void;
    const promise = new Promise<ReconcileResult>((res, rej) => {
      resolve = res;
      reject = rej;
    });
    this.followUp = { promise, resolve, reject };
    return promise;
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
        coalesced: false,
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
        coalesced: false,
        reason: "validation",
      };
    }

    const changed = changedSections(this.lastSnapshot, snapshot);
    const publish = await this.publisher.publish(snapshot);
    if (publish.published) {
      this.lastSnapshot = snapshot;
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
      coalesced: false,
      reason: publish.published ? undefined : publish.reason,
    };
    this.lastResult = result;
    this.lastBuildAt = Date.now();
    this.logger.log(
      `Shadow reconciliation (${reason}): version=${snapshot.version} changed=[${changed.join(",")}] parity=${result.parity === null ? "n/a" : result.parity.toFixed(4)}`,
    );
    return result;
  }

  /** Health/metrics view of the most recent reconciliation. */
  status(): "healthy" | "unhealthy" {
    if (!this.config.shadowModeEnabled) return "healthy";
    // A replica that does not hold the lease is a standby: it is not supposed
    // to build, so failing readiness would make multi-replica deploys flap.
    if (!this.lease.isHolder) return "healthy";
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
      last_build_at:
        this.lastBuildAt === null
          ? null
          : new Date(this.lastBuildAt).toISOString(),
      parity: this.lastResult?.parity ?? null,
      changed_sections: this.lastResult?.changed ?? [],
    };
  }
}
