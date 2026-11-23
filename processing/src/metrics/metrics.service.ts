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
 * Owns the Prometheus registry. Metric names match the Python producer so the
 * existing Grafana dashboards and alerts keep working after the cutover.
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

  private readonly shadowParity = new Gauge({
    name: "processing_shadow_parity_rate",
    help: "Field-level parity between the Processing and legacy snapshots",
    registers: [this.registry],
  });
  private readonly shadowMismatches = new Counter({
    name: "processing_shadow_mismatch_total",
    help: "Field-level mismatches found while comparing snapshots",
    labelNames: ["section", "field"],
    registers: [this.registry],
  });
  private readonly shadowComparisons = new Counter({
    name: "processing_shadow_comparisons_total",
    help: "Shadow comparisons by outcome",
    labelNames: ["result"],
    registers: [this.registry],
  });
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
    labelNames: ["job", "result"],
    registers: [this.registry],
  });
  private readonly jobDuration = new Histogram({
    name: "processing_job_duration_seconds",
    help: "Scheduled job execution duration",
    labelNames: ["job"],
    buckets: [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
    registers: [this.registry],
  });

  constructor(
    @Inject(processingConfig.KEY) config: ConfigType<typeof processingConfig>,
  ) {
    collectDefaultMetrics({ register: this.registry });
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

  setShadowParity(rate: number): void {
    this.shadowParity.set(rate);
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
    this.jobExecutions.labels({ job, result }).inc();
    this.jobDuration.labels({ job }).observe(seconds);
  }
}
