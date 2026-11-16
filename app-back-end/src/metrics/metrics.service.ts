import { Inject, Injectable } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import {
  Counter,
  Gauge,
  Registry,
  collectDefaultMetrics,
} from "@prometheus-io/client";
import { appConfig } from "../config/app.config.js";
import {
  DashboardSnapshotMetrics,
  SnapshotReconciliationResult,
} from "../shared.js";

/**
 * Owns the Prometheus registry. Metric names match the Python service so the
 * existing Grafana dashboards and alerts keep working after the cutover.
 */
@Injectable()
export class MetricsService implements DashboardSnapshotMetrics {
  readonly registry = new Registry();

  private readonly snapshotAge = new Gauge({
    name: "redis_snapshot_age_seconds",
    help: "Age of the local dashboard snapshot",
    registers: [this.registry],
  });
  private readonly snapshotVersionLag = new Gauge({
    name: "redis_snapshot_version_lag",
    help: "Number of snapshot versions the consumer is behind Redis",
    registers: [this.registry],
  });
  private readonly snapshotCacheMisses = new Counter({
    name: "redis_snapshot_cache_miss_total",
    help: "Dashboard snapshot Redis cache misses",
    registers: [this.registry],
  });
  private readonly snapshotReconciliations = new Counter({
    name: "redis_snapshot_reconciliation_total",
    help: "Dashboard snapshot reconciliation outcomes",
    labelNames: ["result"],
    registers: [this.registry],
  });

  constructor(@Inject(appConfig.KEY) config: ConfigType<typeof appConfig>) {
    collectDefaultMetrics({ register: this.registry });
    new Gauge({
      name: "service_version_info",
      help: "Service version information",
      labelNames: ["service", "version"],
      registers: [this.registry],
    })
      .labels({ service: "app-back-end", version: config.version })
      .set(1);
  }

  cacheMiss(): void {
    this.snapshotCacheMisses.inc();
  }

  reconciliation(result: SnapshotReconciliationResult): void {
    this.snapshotReconciliations.labels({ result }).inc();
  }

  setSnapshotState(ageSeconds: number | null, versionLag: number): void {
    this.snapshotAge.set(ageSeconds ?? 0);
    this.snapshotVersionLag.set(versionLag);
  }
}
