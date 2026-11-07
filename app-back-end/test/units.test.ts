import assert from "node:assert/strict";
import { AddressInfo } from "node:net";
import { test } from "node:test";
import { RedisClientType } from "redis";
import { DashboardService } from "../src/dashboard/dashboard.service.js";
import { parseIsoDateTime } from "../src/http/iso-date.js";
import { RedisThrottlerStorage } from "../src/infrastructure/redis/redis-throttler.storage.js";
import { createMetricsServer } from "../src/metrics/metrics.server.js";
import { MetricsService } from "../src/metrics/metrics.service.js";
import { InternalApiClient } from "../src/shared.js";
import { SnapshotService } from "../src/snapshots/snapshot.service.js";

test("Redis throttler storage fails open when Redis is unavailable", async () => {
  const redis = {
    eval: async () => {
      throw new Error("The client is closed");
    },
  } as unknown as RedisClientType;

  const result = await new RedisThrottlerStorage(redis).increment(
    "client",
    60_000,
    8,
    300_000,
    "default",
  );

  assert.equal(result.isBlocked, false);
  assert.equal(result.totalHits, 0);
});

test("ISO date parsing matches the legacy fromisoformat rules", () => {
  assert.equal(parseIsoDateTime("2026-01-01T00:00:00Z"), Date.UTC(2026, 0, 1));
  assert.equal(parseIsoDateTime("2026-01-01"), Date.UTC(2026, 0, 1));
  assert.equal(
    parseIsoDateTime("2026-01-01 02:00:00.5+0200"),
    Date.UTC(2026, 0, 1, 0, 0, 0, 500),
  );
  assert.equal(parseIsoDateTime("2026-01-01T00:00"), Date.UTC(2026, 0, 1));
  for (const invalid of [
    undefined,
    "",
    "Jan 1 2026",
    "2026-13-01",
    "2026-02-29",
    "2026-01-01T24:00:00",
    "2026-01-01T00:00:00+25:00",
  ]) {
    assert.equal(parseIsoDateTime(invalid), null, String(invalid));
  }
});

test("dashboard service maps snapshot buildings without consulting the internal API", async () => {
  const building = {
    id: "507f1f77bcf86cd799439011",
    name: { uk: "Дім" },
    color: "#fff",
    order: 2,
    hasBoundStation: true,
    batteryPercent: 55,
    chargeSource: "Grid",
  };
  const snapshots = {
    getActiveSnapshot: () => ({
      epoch: 1,
      version: 1,
      generatedAt: new Date().toISOString(),
      buildings: [building],
      config: { title: { uk: "Панель" } },
      outagesSchedules: {},
    }),
  } as unknown as SnapshotService;
  const api = new Proxy(
    {},
    {
      get: () => () => {
        throw new Error("internal API must not be called");
      },
    },
  ) as InternalApiClient;
  const service = new DashboardService(api, snapshots);

  assert.deepEqual(await service.getBuildings(), [
    {
      id: building.id,
      name: building.name,
      color: "#fff",
      hasBoundStation: true,
      order: 2,
    },
  ]);
  const [summary] = await service.getBuildingSummaries({
    buildingIds: [building.id],
  });
  assert.equal(summary.batteryPercent, 55);
  assert.equal(summary.isGridAvailable, null);
  assert.equal(summary.chargeSource, "Grid");
  assert.deepEqual(await service.getDashboardConfig(), {
    title: { uk: "Панель" },
    enableOutagesSchedule: false,
    outagesScheduleQueue: null,
  });
});

test("metrics server exposes only /metrics with the legacy metric names", async () => {
  const metrics = new MetricsService({ version: "2026.11.08" } as never);
  metrics.cacheMiss();
  metrics.reconciliation("ok");
  const snapshots = {
    health: () => ({ snapshotAgeSeconds: 12, versionLag: 2 }),
  } as unknown as SnapshotService;
  const server = createMetricsServer(metrics, snapshots).listen(0);
  try {
    await new Promise((resolve) => server.once("listening", resolve));
    const { port } = server.address() as AddressInfo;
    const body = await (await fetch(`http://127.0.0.1:${port}/metrics`)).text();
    assert.match(body, /redis_snapshot_cache_miss_total 1/);
    assert.match(body, /redis_snapshot_reconciliation_total\{result="ok"\} 1/);
    assert.match(body, /redis_snapshot_age_seconds 12/);
    assert.match(body, /redis_snapshot_version_lag 2/);
    assert.match(
      body,
      /service_version_info\{service="app-back-end",version="2026.11.08"\} 1/,
    );
    const api = await fetch(`http://127.0.0.1:${port}/api/dashboard/buildings`);
    assert.equal(api.status, 404);
  } finally {
    server.close();
  }
});
