import { Inject, Injectable, Logger } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { RedisClientType } from "redis";
import { processingConfig } from "../config/processing.config.js";
import { REDIS_WRITER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";
import {
  LUA_SHADOW_WRITE_SCRIPT,
  SHADOW_EPOCH_KEY,
  SHADOW_INVALIDATION_CHANNEL,
  SHADOW_LEASE_KEY,
  SHADOW_SNAPSHOT_KEY,
  SHADOW_VERSION_COMMITTED_KEY,
  SHADOW_VERSION_NEXT_KEY,
} from "../shared.js";
import { ProcessingLease } from "../lease/processing-lease.service.js";
import { PROCESSING_LEASE } from "../tokens.js";
import {
  BaseSnapshotPublisher,
  PublisherKeys,
  PublishResult,
} from "../snapshot/base-snapshot-publisher.js";

/**
 * Writes snapshots to the isolated `shadow:` key namespace.
 *
 * Every key it touches is derived from the `shadow:` prefix, so a shadow
 * publish can never mutate the production snapshot, epoch or version keys.
 */
@Injectable()
export class ShadowPublisher extends BaseSnapshotPublisher {
  protected readonly logger = new Logger(ShadowPublisher.name);
  protected readonly label = "Shadow";
  protected readonly keys: PublisherKeys = {
    snapshotKey: SHADOW_SNAPSHOT_KEY,
    invalidationChannel: SHADOW_INVALIDATION_CHANNEL,
    leaseKey: SHADOW_LEASE_KEY,
    epochKey: SHADOW_EPOCH_KEY,
    versionNextKey: SHADOW_VERSION_NEXT_KEY,
    versionCommittedKey: SHADOW_VERSION_COMMITTED_KEY,
    writeScript: LUA_SHADOW_WRITE_SCRIPT,
  };

  constructor(
    @Inject(REDIS_WRITER) redis: RedisClientType,
    @Inject(PROCESSING_LEASE) lease: ProcessingLease,
    @Inject(processingConfig.KEY)
    config: ConfigType<typeof processingConfig>,
    metrics: MetricsService,
  ) {
    super(redis, lease, metrics);
  }
}

export type { PublishResult };
