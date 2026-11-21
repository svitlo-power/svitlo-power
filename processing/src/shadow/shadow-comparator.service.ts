import { Inject, Injectable, Logger } from "@nestjs/common";
import { RedisClientType } from "redis";
import {
  DashboardSnapshot,
  SNAPSHOT_KEY,
  SnapshotDiff,
  diffSnapshots,
  isDashboardSnapshot,
} from "../shared.js";
import { REDIS_READER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";

export interface ShadowComparison {
  compared: boolean;
  matches: boolean;
  parity: number;
  comparedFields: number;
  mismatches: number;
  reason?: "no-baseline" | "invalid-baseline" | "read-error";
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

    const diff: SnapshotDiff = diffSnapshots(baseline, snapshot);
    this.record(
      diff.matches,
      diff.parity,
      diff.comparedFields,
      diff.mismatches.length,
    );
    this.logMismatches(diff);
    return {
      compared: true,
      matches: diff.matches,
      parity: diff.parity,
      comparedFields: diff.comparedFields,
      mismatches: diff.mismatches.length,
    };
  }

  private record(
    matches: boolean,
    parity: number,
    comparedFields: number,
    mismatches: number,
    reason?: ShadowComparison["reason"],
  ): ShadowComparison {
    if (reason === "no-baseline" || reason === "read-error") {
      this.metrics.shadowComparison("no-baseline");
      return {
        compared: false,
        matches: false,
        parity: 0,
        comparedFields,
        mismatches,
        reason,
      };
    }
    if (reason === "invalid-baseline") {
      this.metrics.shadowComparison("no-baseline");
      return {
        compared: false,
        matches: false,
        parity: 0,
        comparedFields,
        mismatches,
        reason,
      };
    }
    this.metrics.setShadowParity(parity);
    this.metrics.shadowComparison(matches ? "match" : "mismatch");
    return {
      compared: true,
      matches,
      parity,
      comparedFields,
      mismatches,
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
      if (this.mismatchLogs >= MISMATCH_LOG_LIMIT_PER_MINUTE) return;
      this.mismatchLogs += 1;
      this.metrics.shadowMismatch(mismatch.section, mismatch.field);
      this.logger.warn(
        `Shadow mismatch ${mismatch.section}.${mismatch.field}: expected ${JSON.stringify(mismatch.expected)} got ${JSON.stringify(mismatch.actual)}`,
      );
    }
  }
}
