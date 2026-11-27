import {
  Inject,
  Injectable,
  Logger,
  OnApplicationBootstrap,
  OnModuleDestroy,
} from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { RedisClientType } from "redis";
import { processingConfig } from "../config/processing.config.js";
import { MetricsService } from "../metrics/metrics.service.js";
import {
  SNAPSHOT_REFRESH_CHANNEL,
  parseSnapshotRefreshNotification,
} from "../shared.js";
import { REDIS_SUBSCRIBER } from "../tokens.js";
import { RefreshCoordinator } from "./refresh-coordinator.service.js";

/**
 * Receives "data changed" notifications from the legacy back-end.
 *
 * The legacy producer used to call `refresh_and_publish()` inline from about a
 * dozen in-process sites. After the cutover those calls cannot reach Processing,
 * so the back-end publishes a hint here instead and this subscriber funnels it
 * into the same `RefreshCoordinator.request()` path the HTTP trigger uses.
 *
 * Properties the design depends on:
 * - **Fire and forget.** The publisher never awaits Processing, so a subscriber
 *   that is down cannot fail an admin write.
 * - **The payload is a hint.** Only `reason` is used; MongoDB is re-read.
 * - **Coalescing.** Bursts fold into one build through the coordinator.
 * - **At least once.** Duplicates are harmless: the build is idempotent and
 *   version allocation is monotonic.
 */
@Injectable()
export class SnapshotRefreshSubscriber
  implements OnApplicationBootstrap, OnModuleDestroy
{
  private readonly logger = new Logger(SnapshotRefreshSubscriber.name);
  private stopping = false;

  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    @Inject(REDIS_SUBSCRIBER) private readonly subscriber: RedisClientType,
    private readonly coordinator: RefreshCoordinator,
    private readonly metrics: MetricsService,
  ) {}

  async onApplicationBootstrap(): Promise<void> {
    if (!this.config.shadowModeEnabled) {
      this.logger.log(
        "Snapshot refresh subscription disabled: shadow mode is off",
      );
      return;
    }
    try {
      // The payload is delivered through the subscribe callback, not the
      // `message` event: node-redis v4+ removed that event, so a listener
      // attached with `on("message")` never fires and every hint would be
      // silently dropped.
      //
      // The callback signature is `(message, channel)` — the payload first.
      await this.subscriber.subscribe(
        SNAPSHOT_REFRESH_CHANNEL,
        (raw: string) => {
          void this.handleMessage(raw);
        },
      );
    } catch (error) {
      // A subscription that cannot be established must not stop the service:
      // the HTTP trigger and the reconciliation cron still refresh snapshots.
      this.logger.error(
        `Unable to subscribe to ${SNAPSHOT_REFRESH_CHANNEL}: ${(error as Error).message}`,
      );
      return;
    }
    this.logger.log(`Listening on ${SNAPSHOT_REFRESH_CHANNEL}`);
  }

  async onModuleDestroy(): Promise<void> {
    this.stopping = true;
    try {
      // `onModuleDestroy` runs while the Redis clients are being closed, so a
      // rejection here is expected and must not mask the shutdown.
      await this.subscriber.unsubscribe(SNAPSHOT_REFRESH_CHANNEL);
    } catch {
      // The client is already closing; nothing left to do.
    }
  }

  /**
   * Turns one notification into a coalesced refresh request.
   *
   * Failures are recorded and swallowed: the publisher is fire-and-forget, so a
   * rejected build must not surface as an unhandled rejection on the shared
   * client's event loop.
   */
  async handleMessage(raw: string | Buffer): Promise<void> {
    if (this.stopping) return;
    const notification = parseSnapshotRefreshNotification(
      typeof raw === "string" ? raw : raw.toString("utf8"),
    );
    if (notification === null) {
      this.metrics.refreshNotification("invalid");
      this.logger.warn("Discarding an unusable snapshot refresh notification");
      return;
    }
    this.metrics.refreshNotification(notification.reason);
    try {
      const result = await this.coordinator.request(
        notification.reason,
        notification.source,
      );
      // Only a published version acknowledges a hint. A standby replica
      // (`no-lease`), a validation failure or a CAS/lease rejection all settle
      // with `published: false` and version 0; stamping the gauge for those
      // would report a version that was never written and hide a broken path.
      if (result.published) {
        this.metrics.setRefreshAcknowledgement(
          result.version,
          Date.now() / 1000,
        );
      } else if (result.reason === "no-lease") {
        // A standby replica is not an error: with N replicas every hint would
        // otherwise add N-1 "errors" indistinguishable from real failures.
      } else {
        this.metrics.refreshNotificationError(notification.reason);
      }
    } catch (error) {
      this.metrics.refreshNotificationError(notification.reason);
      this.logger.error(
        `Snapshot refresh (${notification.reason}) failed: ${(error as Error).message}`,
      );
    }
  }
}
