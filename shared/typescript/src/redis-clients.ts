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

export interface DashboardSnapshot {
  epoch: number;
  version: number;
  generatedAt: string;
  buildings: Array<Record<string, unknown> & { id: string }>;
  config: {
    title: Record<string, string>;
    outagesSchedule?: {
      enable: boolean;
      regionId: number;
      dsoId: number;
      queue: string;
    } | null;
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
}

export class DashboardSnapshotClient {
  static readonly snapshotKey = "cache:dashboard:v1:global";
  static readonly invalidationChannel = "cache:dashboard:v1:invalidations";

  private snapshot: DashboardSnapshot | null = null;
  private subscribed = false;
  private timer: ReturnType<typeof setInterval> | undefined;
  private lastRefreshAt = 0;
  private stopped = true;
  private notificationWaiter: (() => void) | null = null;

  constructor(
    private readonly reader: SnapshotRedisReader,
    private readonly subscriber: RedisSubscription,
    private readonly refreshUrl: string,
    private readonly staleThresholdSeconds = 300,
    private readonly requestedBy = "app-back-end",
    private readonly fetcher: typeof fetch = fetch,
  ) {}

  async start(): Promise<void> {
    this.stopped = false;
    try {
      await this.subscriber.subscribe(
        DashboardSnapshotClient.invalidationChannel,
        (message) => this.onInvalidation(message),
      );
      this.subscribed = true;
    } catch {
      this.subscribed = false;
    }
    if (await this.reconcile()) await this.refreshOnMiss();
    this.timer = setInterval(() => {
      void this.reconciliationCycle();
      if (!this.subscribed) void this.subscribeAgain();
    }, 60_000);
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

  isStale(): boolean {
    if (!this.snapshot) return true;
    return (
      (Date.now() - Date.parse(this.snapshot.generatedAt)) / 1000 >
      this.staleThresholdSeconds
    );
  }

  health(): DashboardSnapshotHealth {
    const subscribed = this.subscribed && this.subscriber.isReady !== false;
    return {
      status:
        this.snapshot && subscribed && !this.isStale()
          ? "healthy"
          : "unhealthy",
      localEpoch: this.snapshot?.epoch ?? 0,
      localVersion: this.snapshot?.version ?? 0,
      versionLag: 0,
      redisEpoch: this.snapshot?.epoch ?? 0,
      redisVersion: this.snapshot?.version ?? 0,
      snapshotAgeSeconds: this.snapshot
        ? Math.max(
            0,
            (Date.now() - Date.parse(this.snapshot.generatedAt)) / 1000,
          )
        : null,
      isStale: this.isStale(),
      subscribed,
    };
  }

  async reconcile(): Promise<boolean> {
    try {
      const raw = await this.reader.get(DashboardSnapshotClient.snapshotKey);
      if (!raw) return true;
      const next = JSON.parse(raw) as DashboardSnapshot;
      if (!this.isSnapshot(next)) return false;
      if (
        !this.snapshot ||
        next.epoch > this.snapshot.epoch ||
        (next.epoch === this.snapshot.epoch &&
          next.version > this.snapshot.version)
      ) {
        this.snapshot = next;
      }
      return false;
    } catch {
      return false;
    }
  }

  private async subscribeAgain(): Promise<void> {
    if (this.stopped || this.subscribed) return;
    try {
      await this.subscriber.subscribe(
        DashboardSnapshotClient.invalidationChannel,
        (message) => this.onInvalidation(message),
      );
      this.subscribed = true;
      await this.reconcile();
    } catch {
      this.subscribed = false;
    }
  }

  private async reconciliationCycle(): Promise<void> {
    if (await this.reconcile()) await this.refreshOnMiss();
  }

  private onInvalidation(message: string): void {
    try {
      const notification = JSON.parse(message) as { key?: string };
      if (
        notification.key &&
        notification.key !== DashboardSnapshotClient.snapshotKey
      )
        return;
      this.notificationWaiter?.();
      this.notificationWaiter = null;
      void this.reconcile();
    } catch {
      // Ignore malformed invalidations; periodic reconciliation repairs missed events.
    }
  }

  private async refreshOnMiss(): Promise<void> {
    if (Date.now() - this.lastRefreshAt < 60_000) return;
    this.lastRefreshAt = Date.now();
    let resolveNotification: (() => void) | null = null;
    const notified = new Promise<void>((resolve) => {
      resolveNotification = resolve;
    });
    this.notificationWaiter = () => resolveNotification?.();
    try {
      const response = await this.fetcher(this.refreshUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          reason: "cache-miss",
          requestedBy: this.requestedBy,
        }),
        signal: AbortSignal.timeout(5_000),
      });
      if (!response.ok)
        throw new Error(
          `Refresh request failed with status ${response.status}`,
        );
      let timeout: ReturnType<typeof setTimeout> | undefined;
      await Promise.race([
        notified,
        new Promise<void>((resolve) => {
          timeout = setTimeout(resolve, 5_000);
        }),
      ]);
      if (timeout) clearTimeout(timeout);
    } catch {
      // The next reconciliation retries after the cooldown; domain requests use the internal API.
    } finally {
      this.notificationWaiter = null;
    }
    await this.reconcile();
  }

  private isSnapshot(value: DashboardSnapshot): boolean {
    return (
      Number.isInteger(value?.epoch) &&
      Number.isInteger(value?.version) &&
      typeof value.generatedAt === "string" &&
      Array.isArray(value.buildings) &&
      typeof value.config === "object" &&
      value.config !== null &&
      typeof value.outagesSchedules === "object" &&
      value.outagesSchedules !== null
    );
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
