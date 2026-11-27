import { Inject, Injectable, Logger } from "@nestjs/common";
import { RedisClientType } from "redis";
import { REDIS_WRITER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";
import {
  EPOCH_KEY,
  INVALIDATION_CHANNEL,
  LUA_WRITE_SCRIPT,
  LEASE_KEY,
  SNAPSHOT_KEY,
  VERSION_COMMITTED_KEY,
  VERSION_NEXT_KEY,
} from "../shared.js";
import { ProcessingLease } from "../lease/processing-lease.service.js";
import { PROCESSING_LEASE } from "../tokens.js";
import {
  BaseSnapshotPublisher,
  PublisherKeys,
  PublishResult,
} from "./base-snapshot-publisher.js";

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
export class SnapshotPublisher extends BaseSnapshotPublisher {
  protected readonly logger = new Logger(SnapshotPublisher.name);
  protected readonly label = "Snapshot";
  protected readonly keys: PublisherKeys = {
    snapshotKey: SNAPSHOT_KEY,
    invalidationChannel: INVALIDATION_CHANNEL,
    leaseKey: LEASE_KEY,
    epochKey: EPOCH_KEY,
    versionNextKey: VERSION_NEXT_KEY,
    versionCommittedKey: VERSION_COMMITTED_KEY,
    writeScript: LUA_WRITE_SCRIPT,
  };

  constructor(
    @Inject(REDIS_WRITER) redis: RedisClientType,
    @Inject(PROCESSING_LEASE) lease: ProcessingLease,
    metrics: MetricsService,
  ) {
    super(redis, lease, metrics);
  }
}

export type { PublishResult };
