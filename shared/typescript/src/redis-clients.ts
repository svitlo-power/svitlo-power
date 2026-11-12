export interface SnapshotRedisReader {
  get(key: string): Promise<string | null>;
}

export interface RedisSubscription {
  readonly isReady?: boolean;
  subscribe(
    channel: string,
    listener: (message: string) => void,
  ): Promise<unknown>;
  unsubscribe(channel: string): Promise<unknown>;
}

export interface OutagesScheduleConfigSnapshot {
  enable: boolean;
  regionId: number;
  dsoId: number;
  queue: string;
}

export interface BuildingSnapshot {
  id: string;
  name: Record<string, string>;
  color: string;
  order: number;
  hasBoundStation: boolean;
  isGridAvailable?: boolean | null;
  gridAvailabilityPct?: number | null;
  hasMixedReporterStates?: boolean | null;
  isCharging?: boolean | null;
  isDischarging?: boolean | null;
  isOffline?: boolean | null;
  batteryPercent?: number | null;
  consumptionPower?: string | null;
  batteryDischargeTime?: string | null;
  batteryChargeTime?: string | null;
  chargeSource: string;
  chargePower?: number | null;
}

export interface DashboardSnapshot {
  epoch: number;
  version: number;
  generatedAt: string;
  buildings: BuildingSnapshot[];
  config: {
    title: Record<string, string>;
    outagesSchedule?: OutagesScheduleConfigSnapshot | null;
  };
  outagesSchedules: Record<string, Record<string, unknown>>;
}

export interface DashboardSnapshotHealth {
  status: "healthy" | "unhealthy";
  localEpoch: number;
  localVersion: number;
  versionLag: number;
  redisEpoch: number;
  redisVersion: number;
  snapshotAgeSeconds: number | null;
  isStale: boolean;
  subscribed: boolean;
  lastNotificationAt: string | null;
}

export type SnapshotReconciliationResult = "ok" | "miss" | "stale" | "error";

/** Framework-independent hooks so callers can export metrics with any library. */
export interface DashboardSnapshotMetrics {
  cacheMiss?(): void;
  reconciliation?(result: SnapshotReconciliationResult): void;
}

export interface DashboardSnapshotClientOptions {
  reader: SnapshotRedisReader;
  subscriber: RedisSubscription;
  refreshUrl: string;
  staleThresholdSeconds?: number;
  requestedBy?: string;
  reconciliationIntervalMs?: number;
  refreshWaitMs?: number;
  /** Lag (in versions) above which the consumer is unhealthy once it persists for this long. */
  versionLagGraceMs?: number;
  metrics?: DashboardSnapshotMetrics;
  fetcher?: typeof fetch;
  now?: () => number;
}

const CACHE_MISS_REFRESH_COOLDOWN_MS = 60_000;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isBuildingSnapshot(value: unknown): value is BuildingSnapshot {
  return (
    isRecord(value) &&
    typeof value.id === "string" &&
    /^[0-9a-f]{24}$/.test(value.id) &&
    isRecord(value.name) &&
    typeof value.color === "string" &&
    Number.isInteger(value.order) &&
    typeof value.hasBoundStation === "boolean" &&
    typeof value.chargeSource === "string"
  );
}

export function isDashboardSnapshot(
  value: unknown,
): value is DashboardSnapshot {
  return (
    isRecord(value) &&
    Number.isInteger(value.epoch) &&
    Number.isInteger(value.version) &&
    typeof value.generatedAt === "string" &&
    Number.isFinite(Date.parse(value.generatedAt)) &&
    Array.isArray(value.buildings) &&
    value.buildings.every(isBuildingSnapshot) &&
    isRecord(value.config) &&
    isRecord(value.config.title) &&
    isRecord(value.outagesSchedules)
  );
}

export class DashboardSnapshotClient {
  static readonly snapshotKey = "cache:dashboard:v1:global";
  static readonly invalidationChannel = "cache:dashboard:v1:invalidations";

  private readonly reader: SnapshotRedisReader;
  private readonly subscriber: RedisSubscription;
  private readonly refreshUrl: string;
  private readonly staleThresholdSeconds: number;
  private readonly requestedBy: string;
  private readonly reconciliationIntervalMs: number;
  private readonly refreshWaitMs: number;
  private readonly versionLagGraceMs: number;
  private readonly metrics: DashboardSnapshotMetrics;
  private readonly fetcher: typeof fetch;
  private readonly now: () => number;

  private snapshot: DashboardSnapshot | null = null;
  private redisEpoch = 0;
  private redisVersion = 0;
  private versionLagSince: number | null = null;
  private lastNotificationAt: number | null = null;
  private subscribed = false;
  private timer: ReturnType<typeof setInterval> | undefined;
  private lastRefreshAt: number | null = null;
  private stopped = true;
  private notificationWaiter: (() => void) | null = null;

  constructor(options: DashboardSnapshotClientOptions) {
    this.reader = options.reader;
    this.subscriber = options.subscriber;
    this.refreshUrl = options.refreshUrl;
    this.staleThresholdSeconds = options.staleThresholdSeconds ?? 300;
    this.requestedBy = options.requestedBy ?? "app-back-end";
    this.reconciliationIntervalMs = options.reconciliationIntervalMs ?? 60_000;
    this.refreshWaitMs = options.refreshWaitMs ?? 5_000;
    this.versionLagGraceMs = options.versionLagGraceMs ?? 60_000;
    this.metrics = options.metrics ?? {};
    this.fetcher = options.fetcher ?? fetch;
    this.now = options.now ?? Date.now;
  }

  async start(): Promise<void> {
    this.stopped = false;
    await this.subscribe();
    if (await this.reconcile()) await this.refreshOnMiss();
    this.timer = setInterval(() => {
      void this.reconciliationCycle();
    }, this.reconciliationIntervalMs);
    this.timer.unref?.();
  }

  async stop(): Promise<void> {
    this.stopped = true;
    if (this.timer) clearInterval(this.timer);
    this.timer = undefined;
    if (this.subscribed) {
      await this.subscriber
        .unsubscribe(DashboardSnapshotClient.invalidationChannel)
        .catch(() => undefined);
    }
    this.subscribed = false;
  }

  getSnapshot(): DashboardSnapshot | null {
    return this.snapshot;
  }

  getOutageSchedule(queue: string): Record<string, unknown> | null {
    return this.snapshot?.outagesSchedules[queue] ?? null;
  }

  get epoch(): number {
    return this.snapshot?.epoch ?? 0;
  }

  get version(): number {
    return this.snapshot?.version ?? 0;
  }

  get versionLag(): number {
    if (this.redisEpoch !== this.epoch) return 0;
    return Math.max(0, this.redisVersion - this.version);
  }

  ageSeconds(): number | null {
    if (!this.snapshot) return null;
    return Math.max(
      0,
      (this.now() - Date.parse(this.snapshot.generatedAt)) / 1000,
    );
  }

  isStale(): boolean {
    const age = this.ageSeconds();
    return age === null || age > this.staleThresholdSeconds;
  }

  health(): DashboardSnapshotHealth {
    const subscribed = this.subscribed && this.subscriber.isReady !== false;
    const lag = this.versionLag;
    const lagPersisting =
      lag > 1 &&
      this.versionLagSince !== null &&
      this.now() - this.versionLagSince > this.versionLagGraceMs;
    const epochMismatch =
      this.redisEpoch !== 0 && this.redisEpoch !== this.epoch;
    const healthy =
      this.snapshot !== null &&
      subscribed &&
      !this.isStale() &&
      !epochMismatch &&
      !lagPersisting;
    return {
      status: healthy ? "healthy" : "unhealthy",
      localEpoch: this.epoch,
      localVersion: this.version,
      versionLag: lag,
      redisEpoch: this.redisEpoch,
      redisVersion: this.redisVersion,
      snapshotAgeSeconds: this.ageSeconds(),
      isStale: this.isStale(),
      subscribed,
      lastNotificationAt:
        this.lastNotificationAt === null
          ? null
          : new Date(this.lastNotificationAt).toISOString(),
    };
  }

  /** Reads Redis and adopts only newer snapshots. Returns true on a cache miss. */
  async reconcile(): Promise<boolean> {
    let raw: string | null;
    try {
      raw = await this.reader.get(DashboardSnapshotClient.snapshotKey);
    } catch {
      this.metrics.reconciliation?.("error");
      return false;
    }
    if (!raw) {
      this.metrics.cacheMiss?.();
      this.metrics.reconciliation?.("miss");
      return true;
    }

    let next: unknown;
    try {
      next = JSON.parse(raw);
    } catch {
      next = null;
    }
    if (!isDashboardSnapshot(next)) {
      this.metrics.reconciliation?.("error");
      return false;
    }

    this.redisEpoch = next.epoch;
    this.redisVersion = next.version;
    if (this.compare(next) > 0) this.snapshot = next;
    this.trackVersionLag();
    if (this.compare(next) < 0) {
      this.metrics.reconciliation?.("stale");
      return false;
    }
    this.metrics.reconciliation?.("ok");
    return false;
  }

  private trackVersionLag(): void {
    if (this.versionLag > 1) this.versionLagSince ??= this.now();
    else this.versionLagSince = null;
  }

  /** Positive when `candidate` is newer than the local snapshot. */
  private compare(candidate: { epoch: number; version: number }): number {
    return candidate.epoch !== this.epoch
      ? candidate.epoch - this.epoch
      : candidate.version - this.version;
  }

  private async subscribe(): Promise<void> {
    if (this.stopped || this.subscribed) return;
    try {
      await this.subscriber.subscribe(
        DashboardSnapshotClient.invalidationChannel,
        (message) => this.onInvalidation(message),
      );
      this.subscribed = true;
    } catch {
      this.subscribed = false;
    }
  }

  private async reconciliationCycle(): Promise<void> {
    if (!this.subscribed) await this.subscribe();
    if (await this.reconcile()) await this.refreshOnMiss();
  }

  private onInvalidation(message: string): void {
    let notification: unknown;
    try {
      notification = JSON.parse(message);
    } catch {
      return;
    }
    if (!isRecord(notification)) return;
    const key = notification.key ?? DashboardSnapshotClient.snapshotKey;
    if (key !== DashboardSnapshotClient.snapshotKey) return;
    const epoch = Number(notification.epoch);
    const version = Number(notification.version);
    if (!Number.isInteger(epoch) || !Number.isInteger(version)) return;

    this.lastNotificationAt = this.now();
    // Notifications announce the newest version even when the follow-up Redis read fails.
    if (
      epoch > this.redisEpoch ||
      (epoch === this.redisEpoch && version > this.redisVersion)
    ) {
      this.redisEpoch = epoch;
      this.redisVersion = version;
      this.trackVersionLag();
    }
    const waiter = this.notificationWaiter;
    this.notificationWaiter = null;
    if (this.compare({ epoch, version }) > 0) {
      void this.reconcile().finally(() => waiter?.());
    } else {
      waiter?.();
    }
  }

  private async refreshOnMiss(): Promise<void> {
    const now = this.now();
    if (
      this.lastRefreshAt !== null &&
      now - this.lastRefreshAt < CACHE_MISS_REFRESH_COOLDOWN_MS
    ) {
      return;
    }
    this.lastRefreshAt = now;
    const notified = new Promise<void>((resolve) => {
      this.notificationWaiter = resolve;
    });
    let timeout: ReturnType<typeof setTimeout> | undefined;
    try {
      const response = await this.fetcher(this.refreshUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: "cache-miss",
          requestedBy: this.requestedBy,
        }),
        signal: AbortSignal.timeout(this.refreshWaitMs),
      });
      if (!response.ok) return;
      await Promise.race([
        notified,
        new Promise<void>((resolve) => {
          timeout = setTimeout(resolve, this.refreshWaitMs);
        }),
      ]);
    } catch {
      // The next reconciliation retries after the cooldown; domain requests use the internal API.
      return;
    } finally {
      if (timeout) clearTimeout(timeout);
      this.notificationWaiter = null;
    }
    await this.reconcile();
  }
}

export interface RedisEvent {
  type: string;
  data: Record<string, unknown>;
  private?: boolean;
  user?: string | null;
}

export type EventSubscription = (
  channel: string,
  listener: (message: string) => void,
) => Promise<unknown>;

export class RedisEventsClient {
  static readonly publicChannel = "sse_public";
  static readonly privateChannel = "sse_private";
  private readonly channels = [
    RedisEventsClient.publicChannel,
    RedisEventsClient.privateChannel,
  ];

  constructor(private readonly subscribe: EventSubscription) {}

  async start(
    onEvent: (channel: string, event: RedisEvent) => void,
  ): Promise<void> {
    for (const channel of this.channels) {
      await this.subscribe(channel, (message) => {
        try {
          const event = JSON.parse(message) as RedisEvent;
          if (
            typeof event.type === "string" &&
            event.data &&
            typeof event.data === "object"
          ) {
            onEvent(channel, event);
          }
        } catch {
          // Ignore malformed pub/sub payloads and keep the subscription alive.
        }
      });
    }
  }
}
