import { Logger } from "@nestjs/common";
import { RedisClientType } from "redis";
import { MetricsService } from "../metrics/metrics.service.js";
import {
  DashboardSnapshot,
  SNAPSHOT_TTL_SECONDS,
  parseShadowWriteResult,
  stringifySnapshot,
} from "../shared.js";
import { ProcessingLease } from "../lease/processing-lease.service.js";

export interface PublishResult {
  published: boolean;
  reason: string;
}

/** The Redis keys and Lua script one publisher writes through. */
export interface PublisherKeys {
  snapshotKey: string;
  invalidationChannel: string;
  leaseKey: string;
  epochKey: string;
  versionNextKey: string;
  versionCommittedKey: string;
  writeScript: string;
}

/**
 * Shared snapshot write logic for the shadow and production publishers.
 *
 * The two differ only in their key set and Lua script, so the fencing, CAS,
 * version seeding and metrics live here to stop them drifting apart (for
 * example a fix to `initialiseVersionKeys` applied to only one).
 */
export abstract class BaseSnapshotPublisher {
  protected abstract readonly logger: Logger;
  protected abstract readonly keys: PublisherKeys;
  /** Human-readable name used in log lines. */
  protected abstract readonly label: string;

  constructor(
    protected readonly redis: RedisClientType,
    protected readonly lease: ProcessingLease,
    protected readonly metrics: MetricsService,
  ) {}

  /** Allocates the next snapshot version, mirroring the legacy `INCR`. */
  async nextVersion(): Promise<number> {
    return this.redis.incr(this.keys.versionNextKey);
  }

  /**
   * Seeds the epoch and version keys. The epoch is monotonic across restarts,
   * including hosts with a slow clock, exactly like the legacy
   * `_init_version_keys`.
   */
  async initialiseVersionKeys(startTimeMs: number): Promise<number> {
    const { epochKey, snapshotKey, versionNextKey, versionCommittedKey } =
      this.keys;
    const existingEpoch = await this.redis.get(epochKey);
    const snapshotJson = await this.redis.get(snapshotKey);
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
    await this.redis.set(epochKey, String(epoch));

    if ((await this.redis.get(versionNextKey)) === null) {
      await this.redis.set(versionNextKey, "1");
    }
    if ((await this.redis.get(versionCommittedKey)) === null) {
      await this.redis.set(versionCommittedKey, "0");
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
        key: this.keys.snapshotKey,
        epoch: snapshot.epoch,
        version: snapshot.version,
        generatedAt: snapshot.generatedAt,
      });
      const result = await this.redis.eval(this.keys.writeScript, {
        keys: [
          this.keys.snapshotKey,
          this.keys.invalidationChannel,
          this.keys.leaseKey,
          this.keys.epochKey,
          this.keys.versionCommittedKey,
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
          `${this.label} publish rejected: ${parsed.reason} (epoch=${snapshot.epoch}, version=${snapshot.version})`,
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
      this.logger.error(
        `${this.label} publish failed: ${(error as Error).message}`,
      );
      this.metrics.writeError("exception");
      return { published: false, reason: "exception" };
    }
  }

  private ageSeconds(snapshot: DashboardSnapshot): number {
    return Math.max(0, (Date.now() - Date.parse(snapshot.generatedAt)) / 1000);
  }
}
