import { Inject, Injectable, Logger, OnModuleDestroy } from "@nestjs/common";
import { RedisClientType } from "redis";
import {
  LEASE_RENEW_INTERVAL_SECONDS,
  LEASE_TTL_SECONDS,
  LUA_LEASE_RELEASE_SCRIPT,
  LUA_LEASE_RENEW_SCRIPT,
} from "../shared.js";
import { REDIS_WRITER } from "../tokens.js";
import { MetricsService } from "../metrics/metrics.service.js";

export interface LeaseOptions {
  key: string;
  instanceId: string;
  ttlSeconds?: number;
  renewIntervalSeconds?: number;
  onAcquired?: () => void;
  onLost?: () => void;
}

/**
 * Redis-backed single-writer lease.
 *
 * `@nestjs/schedule` runs in-process, so every replica would otherwise perform
 * singleton work concurrently. Only the lease holder may build and publish.
 */
@Injectable()
export class ProcessingLease implements OnModuleDestroy {
  private readonly logger = new Logger(ProcessingLease.name);
  private token: string | null = null;
  private timer: NodeJS.Timeout | null = null;
  private stopped = false;
  private readonly acquiredListeners: Array<() => void> = [];

  constructor(
    @Inject(REDIS_WRITER) private readonly redis: RedisClientType,
    private readonly options: LeaseOptions,
    private readonly metrics: MetricsService,
  ) {}

  get isHolder(): boolean {
    return this.token !== null;
  }

  get leaseToken(): string | null {
    return this.token;
  }

  /**
   * Registers a callback that runs after every successful acquisition,
   * including re-acquisitions after losing the lease.
   */
  onAcquired(listener: () => void): void {
    this.acquiredListeners.push(listener);
  }

  /** One-shot acquisition attempt, used at startup and after losing the lease. */
  async acquire(): Promise<boolean> {
    if (this.stopped || this.token !== null) return this.token !== null;
    const ttl = this.options.ttlSeconds ?? LEASE_TTL_SECONDS;
    const result = await this.redis.set(
      this.options.key,
      this.options.instanceId,
      {
        EX: ttl,
        NX: true,
      },
    );
    if (result !== "OK") {
      this.logger.warn("Shadow lease is held by another instance");
      return false;
    }
    this.token = this.options.instanceId;
    this.logger.log(`Shadow lease acquired: ${this.token}`);
    this.metrics.setShadowLeaseHeld(true);
    this.options.onAcquired?.();
    for (const listener of this.acquiredListeners) listener();
    this.startRenewing();
    return true;
  }

  /**
   * Starts the renewal loop. Renewal failures release the lease locally so the
   * next scheduler tick can attempt reacquisition.
   */
  start(): void {
    if (this.timer || this.stopped) return;
    const interval =
      (this.options.renewIntervalSeconds ?? LEASE_RENEW_INTERVAL_SECONDS) *
      1000;
    this.timer = setInterval(() => void this.renew(), interval);
    this.timer.unref?.();
  }

  async renew(): Promise<boolean> {
    if (this.token === null) return false;
    const ttl = this.options.ttlSeconds ?? LEASE_TTL_SECONDS;
    try {
      const result = await this.redis.eval(LUA_LEASE_RENEW_SCRIPT, {
        keys: [this.options.key],
        arguments: [this.token, String(ttl)],
      });
      if (Number(result) === 1) return true;
    } catch (error) {
      // Drop the token: after a Redis outage this instance no longer knows
      // whether it still holds the lease, and the Lua fence would reject the
      // next write anyway. Reporting `lease_held` here would be a lie.
      this.logger.warn(
        `Shadow lease renewal failed, dropping the lease: ${(error as Error).message}`,
      );
      this.lose();
      return false;
    }
    this.lose();
    return false;
  }

  async release(): Promise<void> {
    this.stopRenewing();
    const token = this.token;
    this.token = null;
    // Reported here rather than through `onLost`: a graceful release is not a
    // lost lease, and the gauge must not keep claiming otherwise.
    this.metrics.setShadowLeaseHeld(false);
    if (token === null) return;
    try {
      await this.redis.eval(LUA_LEASE_RELEASE_SCRIPT, {
        keys: [this.options.key],
        arguments: [token],
      });
      this.logger.log("Shadow lease released");
    } catch (error) {
      this.logger.warn(
        `Shadow lease release failed: ${(error as Error).message}`,
      );
    }
  }

  async onModuleDestroy(): Promise<void> {
    this.stopped = true;
    await this.release();
  }

  private lose(): void {
    if (this.token === null) return;
    this.logger.warn("Shadow lease lost");
    this.token = null;
    this.metrics.setShadowLeaseHeld(false);
    this.options.onLost?.();
  }

  private stopRenewing(): void {
    if (!this.timer) return;
    clearInterval(this.timer);
    this.timer = null;
  }

  private startRenewing(): void {
    this.stopRenewing();
    this.start();
  }
}
