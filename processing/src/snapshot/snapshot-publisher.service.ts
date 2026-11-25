import { Inject, Injectable, Logger } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { RedisClientType } from "redis";
import { processingConfig } from "../config/processing.config.js";
import { REDIS_WRITER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";
import {
  DashboardSnapshot,
  EPOCH_KEY,
  INVALIDATION_CHANNEL,
  LUA_WRITE_SCRIPT,
  LEASE_KEY,
  SNAPSHOT_KEY,
  SNAPSHOT_TTL_SECONDS,
  VERSION_COMMITTED_KEY,
  VERSION_NEXT_KEY,
  parseShadowWriteResult,
  stringifySnapshot,
} from "../shared.js";
import { ProcessingLease } from "../lease/processing-lease.service.js";
import { PROCESSING_LEASE } from "../tokens.js";

export interface PublishResult {
  published: boolean;
  reason: string;
}

/**
 * Writes snapshots to the production snapshot keys.
 *
 * Phase 5 makes Processing the authoritative producer. The write itself is the
 * same Lua script the legacy Python producer uses — lease fencing plus
 * compare-and-set on (epoch, committed version) — so a re-enabled legacy
 * publisher cannot interleave a stale write, and a rollback only has to move
 * the lease back.
 */
@Injectable()
export class SnapshotPublisher {
  private readonly logger = new Logger(SnapshotPublisher.name);

  constructor(
    @Inject(REDIS_WRITER) private readonly redis: RedisClientType,
    @Inject(PROCESSING_LEASE) private readonly lease: ProcessingLease,
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    private readonly metrics: MetricsService,
  ) {}

  /** Allocates the next snapshot version, mirroring the legacy `INCR`. */
  async nextVersion(): Promise<number> {
    return this.redis.incr(VERSION_NEXT_KEY);
  }

  /**
   * Seeds the production epoch and version keys. The epoch is monotonic across
   * restarts, including hosts with a slow clock, exactly like the legacy
   * `_init_version_keys`.
   */
  async initialiseVersionKeys(startTimeMs: number): Promise<number> {
    const existingEpoch = await this.redis.get(EPOCH_KEY);
    const snapshotJson = await this.redis.get(SNAPSHOT_KEY);
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
    await this.redis.set(EPOCH_KEY, String(epoch));

    if ((await this.redis.get(VERSION_NEXT_KEY)) === null) {
      await this.redis.set(VERSION_NEXT_KEY, "1");
    }
    if ((await this.redis.get(VERSION_COMMITTED_KEY)) === null) {
      await this.redis.set(VERSION_COMMITTED_KEY, "0");
    }
    return epoch;
  }

  /**
   * Atomically writes the snapshot with lease fencing and CAS on
   * (epoch, committed version).
   */
  async publish(snapshot: DashboardSnapshot): Promise<PublishResult> {
    const token = this.lease.leaseToken;
    if (token === null) {
      this.metrics.writeError("no-lease");
      return { published: false, reason: "no-lease" };
    }

    const startedAt = Date.now();
    try {
      const notification = JSON.stringify({
        key: SNAPSHOT_KEY,
        epoch: snapshot.epoch,
        version: snapshot.version,
        generatedAt: snapshot.generatedAt,
      });
      const result = await this.redis.eval(LUA_WRITE_SCRIPT, {
        keys: [
          SNAPSHOT_KEY,
          INVALIDATION_CHANNEL,
          LEASE_KEY,
          EPOCH_KEY,
          VERSION_COMMITTED_KEY,
        ],
        arguments: [
          // Python's json.dumps always writes floats with a decimal point, so
          // batteryPercent/chargePower must keep theirs to match the contract.
          stringifySnapshot(snapshot),
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
          `Snapshot publish rejected: ${parsed.reason} (epoch=${snapshot.epoch}, version=${snapshot.version})`,
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
      this.logger.error(`Snapshot publish failed: ${(error as Error).message}`);
      this.metrics.writeError("exception");
      return { published: false, reason: "exception" };
    }
  }

  private ageSeconds(snapshot: DashboardSnapshot): number {
    return Math.max(0, (Date.now() - Date.parse(snapshot.generatedAt)) / 1000);
  }
}
