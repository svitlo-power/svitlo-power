import { Inject, Injectable, Logger } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { RedisClientType } from "redis";
import { processingConfig } from "../config/processing.config.js";
import { REDIS_WRITER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";
import {
  DashboardSnapshot,
  LUA_SHADOW_WRITE_SCRIPT,
  SHADOW_EPOCH_KEY,
  SHADOW_INVALIDATION_CHANNEL,
  SHADOW_LEASE_KEY,
  SHADOW_SNAPSHOT_KEY,
  SHADOW_VERSION_COMMITTED_KEY,
  SHADOW_VERSION_NEXT_KEY,
  SNAPSHOT_TTL_SECONDS,
  parseShadowWriteResult,
} from "../shared.js";
import { ProcessingLease } from "../lease/processing-lease.service.js";
import { PROCESSING_LEASE } from "../tokens.js";

export interface ShadowPublishResult {
  published: boolean;
  reason: string;
}

/**
 * Writes snapshots to the isolated `shadow:` key namespace.
 *
 * Every key it touches is derived from the `shadow:` prefix, so a shadow
 * publish can never mutate the production snapshot, epoch or version keys.
 */
@Injectable()
export class ShadowPublisher {
  private readonly logger = new Logger(ShadowPublisher.name);

  constructor(
    @Inject(REDIS_WRITER) private readonly redis: RedisClientType,
    @Inject(PROCESSING_LEASE) private readonly lease: ProcessingLease,
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    private readonly metrics: MetricsService,
  ) {}

  /** Allocates the next shadow version, mirroring the legacy `INCR`. */
  async nextVersion(): Promise<number> {
    return this.redis.incr(SHADOW_VERSION_NEXT_KEY);
  }

  /**
   * Seeds the shadow epoch and version keys. The epoch is monotonic across
   * restarts, including hosts with a slow clock, exactly like the legacy
   * `_init_version_keys`.
   */
  async initialiseVersionKeys(startTimeMs: number): Promise<number> {
    const existingEpoch = await this.redis.get(SHADOW_EPOCH_KEY);
    const snapshotJson = await this.redis.get(SHADOW_SNAPSHOT_KEY);
    let snapshotEpoch = 0;
    if (snapshotJson) {
      try {
        snapshotEpoch =
          (JSON.parse(snapshotJson) as DashboardSnapshot).epoch ?? 0;
      } catch {
        snapshotEpoch = 0;
      }
    }
    const epoch = Math.max(
      startTimeMs,
      Number.parseInt(existingEpoch ?? "0", 10) || 0,
      snapshotEpoch,
    );
    await this.redis.set(SHADOW_EPOCH_KEY, String(epoch));

    if ((await this.redis.get(SHADOW_VERSION_NEXT_KEY)) === null) {
      await this.redis.set(SHADOW_VERSION_NEXT_KEY, "1");
    }
    if ((await this.redis.get(SHADOW_VERSION_COMMITTED_KEY)) === null) {
      await this.redis.set(SHADOW_VERSION_COMMITTED_KEY, "0");
    }
    return epoch;
  }

  /**
   * Atomically writes the snapshot with lease fencing and CAS on
   * (epoch, committed version).
   */
  async publish(snapshot: DashboardSnapshot): Promise<ShadowPublishResult> {
    const token = this.lease.leaseToken;
    if (token === null) {
      this.metrics.writeError("no-lease");
      return { published: false, reason: "no-lease" };
    }

    const startedAt = Date.now();
    try {
      const notification = JSON.stringify({
        key: SHADOW_SNAPSHOT_KEY,
        epoch: snapshot.epoch,
        version: snapshot.version,
        generatedAt: snapshot.generatedAt,
      });
      const result = await this.redis.eval(LUA_SHADOW_WRITE_SCRIPT, {
        keys: [
          SHADOW_SNAPSHOT_KEY,
          SHADOW_INVALIDATION_CHANNEL,
          SHADOW_LEASE_KEY,
          SHADOW_EPOCH_KEY,
          SHADOW_VERSION_COMMITTED_KEY,
        ],
        arguments: [
          JSON.stringify(snapshot),
          notification,
          String(SNAPSHOT_TTL_SECONDS),
          token,
          String(snapshot.epoch),
          String(snapshot.version),
        ],
      });
      this.metrics.observePublishDuration((Date.now() - startedAt) / 1000);

      const parsed = parseShadowWriteResult(result);
      if (!parsed.success) {
        this.logger.warn(
          `Shadow publish rejected: ${parsed.reason} (epoch=${snapshot.epoch}, version=${snapshot.version})`,
        );
        this.metrics.writeError(parsed.reason);
        return { published: false, reason: parsed.reason };
      }
      this.metrics.setSnapshotState(
        snapshot.epoch,
        snapshot.version,
        this.ageSeconds(snapshot),
      );
      return { published: true, reason: parsed.reason };
    } catch (error) {
      this.metrics.observePublishDuration((Date.now() - startedAt) / 1000);
      this.logger.error(`Shadow publish failed: ${(error as Error).message}`);
      this.metrics.writeError("exception");
      return { published: false, reason: "exception" };
    }
  }

  private ageSeconds(snapshot: DashboardSnapshot): number {
    return Math.max(0, (Date.now() - Date.parse(snapshot.generatedAt)) / 1000);
  }
}
