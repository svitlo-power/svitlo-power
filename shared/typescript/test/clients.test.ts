import assert from "node:assert/strict";
import { test } from "node:test";
import {
  DashboardSnapshotClient,
  InternalApiClient,
  InternalApiError,
  RedisEventsClient,
} from "../src/index.js";

test("internal API client sends bearer auth and camelCase body", async () => {
  let observedUrl = "";
  let observedInit: RequestInit | undefined;
  const client = new InternalApiClient(
    "http://internal/internal/v1/app/",
    "service-secret",
    1000,
    async (url, init) => {
      observedUrl = String(url);
      observedInit = init;
      return Response.json({ accepted: true });
    },
  );

  await client.getPowerLogs(
    "507f1f77bcf86cd799439011",
    "2026-01-01T00:00:00Z",
    "2026-01-02T00:00:00Z",
  );

  assert.equal(
    observedUrl,
    "http://internal/internal/v1/app/dashboard/buildings/507f1f77bcf86cd799439011/power-logs",
  );
  assert.equal(
    new Headers(observedInit?.headers).get("authorization"),
    "Bearer service-secret",
  );
  assert.deepEqual(JSON.parse(String(observedInit?.body)), {
    startDate: "2026-01-01T00:00:00Z",
    endDate: "2026-01-02T00:00:00Z",
  });
});

test("internal API client exposes upstream status and detail without hiding failures", async () => {
  const client = new InternalApiClient(
    "http://internal",
    "token",
    1000,
    async () =>
      Response.json({ detail: "Device not registered" }, { status: 404 }),
  );

  await assert.rejects(client.getDevice("device-token"), (error: unknown) => {
    assert.ok(error instanceof InternalApiError);
    assert.equal(error.status, 404);
    assert.equal(error.detail, "Device not registered");
    return true;
  });
});

test("snapshot reconciliation adopts newer versions and rejects older snapshots", async () => {
  let raw = JSON.stringify({
    epoch: 1,
    version: 3,
    generatedAt: new Date().toISOString(),
    buildings: [],
    config: { title: {} },
    outagesSchedules: {},
  });
  const subscriber = {
    subscribe: async () => undefined,
    unsubscribe: async () => undefined,
  };
  const client = new DashboardSnapshotClient({
    reader: { get: async () => raw },
    subscriber,
    refreshUrl: "http://refresh",
  });

  assert.equal(await client.reconcile(), false);
  raw = JSON.stringify({ ...JSON.parse(raw), version: 2 });
  assert.equal(await client.reconcile(), false);
  assert.equal(client.getSnapshot()?.version, 3);
  await client.stop();
});

test("Redis event client ignores malformed messages and forwards known payloads", async () => {
  const listeners = new Map<string, (message: string) => void>();
  const events = new RedisEventsClient(async (channel, listener) => {
    listeners.set(channel, listener);
  });
  const received: string[] = [];

  await events.start((channel, event) =>
    received.push(`${channel}:${event.type}`),
  );
  listeners.get("sse_public")?.("{bad json");
  listeners.get("sse_public")?.('{"type":"updated","data":{}}');

  assert.deepEqual(received, ["sse_public:updated"]);
});

test("snapshot startup subscribes before the initial Redis read", async () => {
  const order: string[] = [];
  const payload = JSON.stringify({
    epoch: 1,
    version: 1,
    generatedAt: new Date().toISOString(),
    buildings: [],
    config: { title: {} },
    outagesSchedules: {},
  });
  const subscriber = {
    subscribe: async () => {
      order.push("subscribe");
    },
    unsubscribe: async () => undefined,
  };
  const client = new DashboardSnapshotClient({
    reader: {
      get: async () => {
        order.push("read");
        return payload;
      },
    },
    subscriber,
    refreshUrl: "http://refresh",
  });

  await client.start();
  assert.deepEqual(order.slice(0, 2), ["subscribe", "read"]);
  assert.equal(client.health().status, "healthy");
  await client.stop();
});

test("snapshot cache miss requests refresh and waits for invalidation", async () => {
  const order: string[] = [];
  let raw: string | null = null;
  let invalidationListener: ((message: string) => void) | undefined;
  const subscriber = {
    subscribe: async (
      _channel: string,
      listener: (message: string) => void,
    ) => {
      order.push("subscribe");
      invalidationListener = listener;
    },
    unsubscribe: async () => undefined,
  };
  const client = new DashboardSnapshotClient({
    reader: {
      get: async () => {
        order.push("read");
        return raw;
      },
    },
    subscriber,
    refreshUrl: "http://refresh",
    fetcher: async (_url, init) => {
      order.push("refresh");
      assert.equal(init?.method, "POST");
      raw = JSON.stringify({
        epoch: 1,
        version: 1,
        generatedAt: new Date().toISOString(),
        buildings: [],
        config: { title: {} },
        outagesSchedules: {},
      });
      invalidationListener?.(
        JSON.stringify({
          key: DashboardSnapshotClient.snapshotKey,
          epoch: 1,
          version: 1,
        }),
      );
      return Response.json({ accepted: true });
    },
  });

  await client.start();
  assert.deepEqual(order.slice(0, 3), ["subscribe", "read", "refresh"]);
  assert.equal(client.getSnapshot()?.version, 1);
  await client.stop();
});

test("internal API client rejects missing credentials and malformed success responses", async () => {
  const missingToken = new InternalApiClient(
    "http://internal",
    "",
    1000,
    async () => {
      throw new Error("request should not be sent");
    },
  );
  const malformedResponse = new InternalApiClient(
    "http://internal",
    "token",
    1000,
    async () => new Response("not json", { status: 200 }),
  );

  await assert.rejects(
    missingToken.getHealth(),
    (error: unknown) =>
      error instanceof InternalApiError && error.status === 503,
  );
  await assert.rejects(
    malformedResponse.getHealth(),
    (error: unknown) =>
      error instanceof InternalApiError && error.status === 502,
  );
});

function snapshotPayload(overrides: Record<string, unknown> = {}): string {
  return JSON.stringify({
    epoch: 1,
    version: 1,
    generatedAt: new Date().toISOString(),
    buildings: [
      {
        id: "507f1f77bcf86cd799439011",
        name: { uk: "Дім" },
        color: "#fff",
        order: 1,
        hasBoundStation: true,
        chargeSource: "None",
      },
    ],
    config: { title: { uk: "Панель" } },
    outagesSchedules: {},
    ...overrides,
  });
}

const idleSubscriber = {
  subscribe: async () => undefined,
  unsubscribe: async () => undefined,
};

test("snapshot client rejects snapshots with unparseable timestamps or malformed buildings", async () => {
  const results: string[] = [];
  let raw = snapshotPayload({ generatedAt: "not-a-date" });
  const client = new DashboardSnapshotClient({
    reader: { get: async () => raw },
    subscriber: idleSubscriber,
    refreshUrl: "http://refresh",
    metrics: { reconciliation: (result) => results.push(result) },
  });

  await client.reconcile();
  raw = snapshotPayload({ buildings: [{ id: "bad" }] });
  await client.reconcile();

  assert.equal(client.getSnapshot(), null);
  assert.equal(client.isStale(), true);
  assert.deepEqual(results, ["error", "error"]);
});

test("snapshot health reports Redis version lag and turns unhealthy when it persists", async () => {
  let now = Date.parse("2026-01-01T00:00:00Z");
  let readFails = false;
  const raw = snapshotPayload({ generatedAt: new Date(now).toISOString() });
  let listener: ((message: string) => void) | undefined;
  const client = new DashboardSnapshotClient({
    reader: {
      get: async () => {
        if (readFails) throw new Error("connection lost");
        return raw;
      },
    },
    subscriber: {
      subscribe: async (_channel, next) => {
        listener = next;
      },
      unsubscribe: async () => undefined,
    },
    refreshUrl: "http://refresh",
    staleThresholdSeconds: 600,
    now: () => now,
  });

  await client.start();
  assert.equal(client.health().status, "healthy");
  assert.equal(client.health().lastNotificationAt, null);

  readFails = true;
  listener?.(JSON.stringify({ epoch: 1, version: 4 }));
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(client.health().versionLag, 3);
  assert.equal(client.health().redisVersion, 4);
  assert.equal(client.health().localVersion, 1);
  assert.equal(client.health().status, "healthy");
  assert.equal(client.health().lastNotificationAt, new Date(now).toISOString());

  now += 61_000;
  assert.equal(client.health().status, "unhealthy");
  await client.stop();
});

test("snapshot client reports cache misses through metrics hooks", async () => {
  let misses = 0;
  const client = new DashboardSnapshotClient({
    reader: { get: async () => null },
    subscriber: idleSubscriber,
    refreshUrl: "http://refresh",
    metrics: { cacheMiss: () => (misses += 1) },
  });

  assert.equal(await client.reconcile(), true);
  assert.equal(misses, 1);
});
