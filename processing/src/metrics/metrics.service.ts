import { Inject, Injectable } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import {
  Counter,
  Gauge,
  Histogram,
  Registry,
  collectDefaultMetrics,
} from "@prometheus-io/client";
import { processingConfig } from "../config/processing.config.js";

/**
 * Owns the Prometheus registry.
 *
 * The snapshot/refresh metric names match the Python producer so the existing
 * Grafana dashboards and alerts keep working after the cutover. While shadow
 * mode is active both services export them, so every panel and alert has to
 * filter on `job`; the shadow-only metrics carry a `processing_shadow_`
 * prefix and never collide.
 */
@Injectable()
export class MetricsService {
  readonly registry = new Registry();

  private readonly buildDuration = new Histogram({
    name: "dashboard_snapshot_build_duration_seconds",
    help: "Time spent building dashboard snapshot",
    buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
    registers: [this.registry],
  });
  private readonly publishDuration = new Histogram({
    name: "dashboard_snapshot_publish_duration_seconds",
    help: "Time spent publishing dashboard snapshot to Redis",
    buckets: [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
    registers: [this.registry],
  });
  private readonly epoch = new Gauge({
    name: "dashboard_snapshot_epoch",
    help: "Current dashboard snapshot epoch (producer start time in milliseconds)",
    registers: [this.registry],
  });
  private readonly version = new Gauge({
    name: "dashboard_snapshot_version",
    help: "Current dashboard snapshot version within epoch",
    registers: [this.registry],
  });
  private readonly ageSeconds = new Gauge({
    name: "dashboard_snapshot_age_seconds",
    help: "Age of current dashboard snapshot in seconds",
    registers: [this.registry],
  });
  private readonly writeErrors = new Counter({
    name: "dashboard_snapshot_write_errors_total",
    help: "Total number of dashboard snapshot write errors",
    labelNames: ["error_type"],
    registers: [this.registry],
  });
  private readonly refreshRequests = new Counter({
    name: "dashboard_refresh_requests_total",
    help: "Total number of dashboard refresh requests",
    labelNames: ["reason"],
    registers: [this.registry],
  });
  private readonly refreshCoalesced = new Counter({
    name: "dashboard_refresh_coalesced_total",
    help: "Total number of coalesced refresh requests",
    registers: [this.registry],
  });
  private readonly refreshNotifications = new Counter({
    name: "processing_refresh_notifications_total",
    help: "Snapshot refresh notifications received from the legacy back-end",
    labelNames: ["reason"],
    registers: [this.registry],
  });
  private readonly refreshNotificationErrors = new Counter({
    name: "processing_refresh_notification_errors_total",
    help: "Snapshot refresh notifications whose build failed",
    labelNames: ["reason"],
    registers: [this.registry],
  });
  /**
   * Version that acknowledged the last notification, created on first write.
   *
   * Registered eagerly it would export `0`, which reads as "version 0 is
   * current" instead of "no notification yet".
   */
  private refreshAcknowledgedVersion: Gauge<string> | null = null;
  private refreshAcknowledgedAt: Gauge<string> | null = null;

  private readonly shadowParity = new Gauge({
    name: "processing_shadow_parity_rate",
    help: "Field-level parity between the Processing and legacy snapshots",
    registers: [this.registry],
  });
  private readonly shadowMismatches = new Counter({
    name: "processing_shadow_mismatch_total",
    help: "Field-level mismatches found while comparing snapshots",
    // The field label is the bare key (for example `batteryPercent`), never
    // `buildings[<index>].<key>`: the index would make the label cardinality
    // grow with the number of buildings.
    labelNames: ["section", "field"],
    registers: [this.registry],
  });
  private readonly shadowComparisons = new Counter({
    name: "processing_shadow_comparisons_total",
    help: "Shadow comparisons by outcome",
    labelNames: ["result"],
    registers: [this.registry],
  });
  private readonly shadowSkew = new Gauge({
    name: "processing_shadow_comparison_skew_seconds",
    help: "Age difference between the compared production and shadow snapshots",
    registers: [this.registry],
  });
  private readonly shadowModeEnabled = new Gauge({
    name: "processing_shadow_mode_enabled",
    help: "1 when shadow mode is enabled on this instance, 0 otherwise",
    registers: [this.registry],
  });
  private readonly shadowLeaseHeld = new Gauge({
    name: "processing_shadow_lease_held",
    help: "1 while this instance holds the shadow lease, 0 otherwise",
    registers: [this.registry],
  });
  private readonly publishEnabled = new Gauge({
    name: "processing_publish_enabled",
    help: "1 when this instance publishes to the production snapshot keys, 0 otherwise",
    registers: [this.registry],
  });
  /**
   * Timestamp gauge behind `shadowLastComparison`, created on first write.
   *
   * A registered gauge is exported as `0`, and an epoch-0 timestamp makes
   * `time() - ts` exceed any freshness threshold. While shadow mode is off the
   * series is therefore absent rather than misleading, and the alert's `and`
   * filters keep it out of the rule anyway.
   *
   * The gauge is cached per registry because `@prometheus-io/client` keeps a
   * module-level metric registry: a second `MetricsService` (tests, or a second
   * app in one process) cannot register the same name again.
   */
  private shadowLastComparisonGauges = new WeakMap<Registry, Gauge<string>>();
  private readonly leaseAcquired = new Counter({
    name: "processing_lease_acquired_total",
    help: "Times the shadow lease has been acquired",
    registers: [this.registry],
  });
  private readonly leaseLost = new Counter({
    name: "processing_lease_lost_total",
    help: "Times the shadow lease has been lost",
    registers: [this.registry],
  });
  private readonly jobExecutions = new Counter({
    name: "processing_job_executions_total",
    help: "Scheduled job executions by outcome",
    // `job` is reserved by Prometheus for the scrape target and is renamed to
    // `exported_job` on the wire, which breaks `sum by (job, ...)` queries.
    labelNames: ["job_name", "result"],
    registers: [this.registry],
  });
  private readonly jobDuration = new Histogram({
    name: "processing_job_duration_seconds",
    help: "Scheduled job execution duration",
    labelNames: ["job_name"],
    buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registers: [this.registry],
  });

  constructor(
    @Inject(processingConfig.KEY) config: ConfigType<typeof processingConfig>,
  ) {
    collectDefaultMetrics({ register: this.registry });
    // An unset gauge is exported as `0`, not as a missing series, so both
    // shadow gauges have to be seeded explicitly: otherwise "no sample yet"
    // reads as 0% parity and as an epoch-0 comparison timestamp, which is what
    // made the freshness alert fire on every restart and on every standby.
    this.shadowParity.set(Number.NaN);
    this.shadowModeEnabled.set(config.shadowModeEnabled ? 1 : 0);
    this.shadowLeaseHeld.set(0);
    this.publishEnabled.set(config.publishEnabled ? 1 : 0);
    if (config.shadowModeEnabled) {
      // A replica that is expected to compare but has not yet completed one is
      // only "not stale" for the first 15 minutes after it starts.
      this.markShadowComparisonTimestamp(Date.now() / 1000);
    }
    new Gauge({
      name: "service_version_info",
      help: "Service version information",
      labelNames: ["service", "version"],
      registers: [this.registry],
    })
      .labels({ service: "processing", version: config.version })
      .set(1);
  }

  observeBuildDuration(seconds: number): void {
    this.buildDuration.observe(seconds);
  }

  observePublishDuration(seconds: number): void {
    this.publishDuration.observe(seconds);
  }

  setSnapshotState(epoch: number, version: number, ageSeconds: number): void {
    this.epoch.set(epoch);
    this.version.set(version);
    this.ageSeconds.set(ageSeconds);
  }

  writeError(errorType: string): void {
    this.writeErrors.labels({ error_type: errorType }).inc();
  }

  refreshRequest(reason: string): void {
    this.refreshRequests.labels({ reason }).inc();
  }

  refreshCoalescedCount(): void {
    this.refreshCoalesced.inc();
  }

  /** Counts a received "data changed" notification by its declared reason. */
  refreshNotification(reason: string): void {
    this.refreshNotifications.labels({ reason }).inc();
  }

  refreshNotificationError(reason: string): void {
    this.refreshNotificationErrors.labels({ reason }).inc();
  }

  /**
   * Records the version that acknowledged a notification.
   *
   * The pair of gauges is what makes a silently broken subscription visible: a
   * subscription that receives nothing looks exactly like "no data changed"
   * unless the acknowledged version and its timestamp are exported.
   */
  setRefreshAcknowledgement(version: number, seconds: number): void {
    this.refreshAcknowledgedVersion ??= new Gauge({
      name: "processing_refresh_acknowledged_version",
      help: "Snapshot version that acknowledged the last refresh notification",
      registers: [this.registry],
    });
    this.refreshAcknowledgedAt ??= new Gauge({
      name: "processing_refresh_acknowledged_timestamp_seconds",
      help: "Unix timestamp of the last acknowledged refresh notification",
      registers: [this.registry],
    });
    this.refreshAcknowledgedVersion.set(version);
    this.refreshAcknowledgedAt.set(seconds);
  }

  setShadowParity(rate: number): void {
    this.shadowParity.set(rate);
    this.markShadowComparisonTimestamp(Date.now() / 1000);
  }

  /**
   * Records when the last comparison completed.
   *
   * The gauge is created on first write so that a deployment with shadow mode
   * off exports no series at all instead of an epoch-0 one.
   */
  private markShadowComparisonTimestamp(seconds: number): void {
    let gauge = this.shadowLastComparisonGauges.get(this.registry);
    if (!gauge) {
      gauge = new Gauge({
        name: "processing_shadow_last_comparison_timestamp_seconds",
        help: "Unix timestamp of the last completed shadow comparison, or of process start while shadow mode is enabled",
        registers: [this.registry],
      });
      this.shadowLastComparisonGauges.set(this.registry, gauge);
    }
    gauge.set(seconds);
  }

  /**
   * Publishes whether this instance currently holds the shadow lease.
   *
   * The freshness alert needs it: only the lease holder is supposed to compare,
   * so a standby must not look like a stalled replica.
   */
  setShadowLeaseHeld(held: boolean): void {
    this.shadowLeaseHeld.set(held ? 1 : 0);
  }

  /**
   * Marks the parity sample as stale without inventing a value.
   *
   * A skipped comparison leaves the previous parity in place, which would show
   * healthy parity from hours ago. The gauge is set to `NaN` — Prometheus
   * parses sample values with `strconv.ParseFloat`, which accepts `nan` in any
   * case, so the series keeps its identity but has no numeric value — and the
   * freshness timestamp is left alone. That keeps `0` meaning "0% parity", so a
   * future `parity < X` alert cannot fire on a skipped comparison, while
   * `time() - processing_shadow_last_comparison_timestamp_seconds` shows the
   * gap.
   *
   * The constructor seeds the same value, so "no sample yet" and "skipped" are
   * indistinguishable and `0` only ever means a real 0% parity.
   */
  markShadowParityStale(): void {
    this.shadowParity.set(Number.NaN);
  }

  setShadowSkew(seconds: number): void {
    this.shadowSkew.set(seconds);
  }

  shadowMismatch(section: string, field: string): void {
    this.shadowMismatches.labels({ section, field }).inc();
  }

  shadowComparison(
    result:
      | "match"
      | "mismatch"
      | "no-baseline"
      | "invalid-baseline"
      | "read-error"
      | "stale-baseline",
  ): void {
    this.shadowComparisons.labels({ result }).inc();
  }

  leaseAcquisition(): void {
    this.leaseAcquired.inc();
  }

  leaseLoss(): void {
    this.leaseLost.inc();
  }

  jobExecution(job: string, result: string, seconds: number): void {
    this.jobExecutions.labels({ job_name: job, result }).inc();
    this.jobDuration.labels({ job_name: job }).observe(seconds);
  }
}
