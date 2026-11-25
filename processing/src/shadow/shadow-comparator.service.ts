import { Inject, Injectable, Logger } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { RedisClientType } from "redis";
import {
  DashboardSnapshot,
  SNAPSHOT_KEY,
  SnapshotDiff,
  diffSnapshots,
  isDashboardSnapshot,
} from "../shared.js";
import { processingConfig } from "../config/processing.config.js";
import { REDIS_READER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";

export interface ShadowComparison {
  compared: boolean;
  matches: boolean;
  parity: number;
  comparedFields: number;
  mismatches: number;
  reason?: "no-baseline" | "invalid-baseline" | "read-error" | "stale-baseline";
  /** Age difference between the production and shadow snapshots, in seconds. */
  skewSeconds?: number;
}

/** How many mismatch samples to log per minute. */
const MISMATCH_LOG_LIMIT_PER_MINUTE = 10;

/**
 * Compares the Processing snapshot with the snapshot the legacy producer
 * published to the production key.
 *
 * The production key is only ever read; the legacy producer stays authoritative
 * throughout shadow validation.
 */
@Injectable()
export class ShadowComparator {
  private readonly logger = new Logger(ShadowComparator.name);
  private mismatchLogs = 0;
  private windowStartedAt = Date.now();

  constructor(
    @Inject(REDIS_READER) private readonly redis: RedisClientType,
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    private readonly metrics: MetricsService,
  ) {}

  async compareWithProduction(
    snapshot: DashboardSnapshot,
  ): Promise<ShadowComparison> {
    let raw: string | null;
    try {
      raw = await this.redis.get(SNAPSHOT_KEY);
    } catch (error) {
      this.logger.warn(
        `Shadow comparison skipped: ${(error as Error).message}`,
      );
      return this.record(false, 0, 0, 0, "read-error");
    }

    if (raw === null) {
      // Empty cache is a first-class scenario: there is nothing to compare yet.
      return this.record(false, 0, 0, 0, "no-baseline");
    }

    let baseline: unknown;
    try {
      baseline = JSON.parse(raw);
    } catch {
      return this.record(false, 0, 0, 0, "invalid-baseline");
    }
    if (!isDashboardSnapshot(baseline)) {
      return this.record(false, 0, 0, 0, "invalid-baseline");
    }

    // The shadow build and the production build never happen at the same
    // instant, so live fields (rolling consumption average, isOffline,
    // batteryPercent) legitimately differ. Comparing across a large skew
    // produces mismatches that say nothing about the port's correctness.
    const skewSeconds = Math.abs(
      (Date.parse(snapshot.generatedAt) - Date.parse(baseline.generatedAt)) /
        1000,
    );
    if (skewSeconds > this.config.comparisonMaxSkewSeconds) {
      this.logger.warn(
        `Shadow comparison skipped: snapshot skew ${Math.round(skewSeconds)}s exceeds ${this.config.comparisonMaxSkewSeconds}s`,
      );
      return this.record(false, 0, 0, 0, "stale-baseline", skewSeconds);
    }

    const diff: SnapshotDiff = diffSnapshots(baseline, snapshot);
    this.record(
      diff.matches,
      diff.parity,
      diff.comparedFields,
      diff.mismatches.length,
      undefined,
      skewSeconds,
    );
    this.logMismatches(diff);
    return {
      compared: true,
      matches: diff.matches,
      parity: diff.parity,
      comparedFields: diff.comparedFields,
      mismatches: diff.mismatches.length,
      skewSeconds,
    };
  }

  private record(
    matches: boolean,
    parity: number,
    comparedFields: number,
    mismatches: number,
    reason?: ShadowComparison["reason"],
    skewSeconds?: number,
  ): ShadowComparison {
    if (reason !== undefined) {
      this.metrics.shadowComparison(reason);
      // Do not leave the previous parity looking current: a skipped comparison
      // must be visible as "no fresh sample", not as healthy parity.
      this.metrics.markShadowParityStale();
      if (skewSeconds !== undefined) this.metrics.setShadowSkew(skewSeconds);
      return {
        compared: false,
        matches: false,
        parity: 0,
        comparedFields,
        mismatches,
        reason,
        skewSeconds,
      };
    }
    this.metrics.setShadowParity(parity);
    if (skewSeconds !== undefined) this.metrics.setShadowSkew(skewSeconds);
    this.metrics.shadowComparison(matches ? "match" : "mismatch");
    return {
      compared: true,
      matches,
      parity,
      comparedFields,
      mismatches,
      skewSeconds,
    };
  }

  private logMismatches(diff: SnapshotDiff): void {
    if (diff.matches) return;
    const now = Date.now();
    if (now - this.windowStartedAt > 60_000) {
      this.windowStartedAt = now;
      this.mismatchLogs = 0;
    }
    for (const mismatch of diff.mismatches) {
      // The metric counts every mismatch; only the log line is rate limited,
      // otherwise processing_shadow_mismatch_total undercounts.
      this.metrics.shadowMismatch(mismatch.section, mismatch.field);
      if (this.mismatchLogs >= MISMATCH_LOG_LIMIT_PER_MINUTE) continue;
      this.mismatchLogs += 1;
      this.logger.warn(
        `Shadow mismatch ${mismatch.section}.${mismatch.field}: expected ${JSON.stringify(mismatch.expected)} got ${JSON.stringify(mismatch.actual)}`,
      );
    }
  }
}
