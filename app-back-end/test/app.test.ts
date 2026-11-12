import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { INestApplication } from "@nestjs/common";
import { Test } from "@nestjs/testing";
import request from "supertest";
import { AppModule } from "../src/app.module.js";
import { appConfig } from "../src/config/app.config.js";
import { createValidationPipe } from "../src/http/validation.pipe.js";
import { setupOpenApi } from "../src/http/openapi.js";
import {
  INTERNAL_API,
  REDIS_READER,
  REDIS_SUBSCRIBER,
  SNAPSHOT_CLIENT,
} from "../src/tokens.js";
import { InternalApiError } from "../src/shared.js";

const api = {
  getBuildings: async () => [
    {
      id: "507f1f77bcf86cd799439011",
      name: { uk: "Дім" },
      color: "#fff",
      hasBoundStation: true,
      order: 1,
    },
  ],
  getBuildingSummaries: async () => [],
  getDashboardConfig: async () => ({
    title: { uk: "Панель" },
    outagesSchedule: { enable: true, regionId: 1, dsoId: 2, queue: "1.1" },
  }),
  getPowerLogs: async () => ({
    periods: [],
    totalAvailableSeconds: 0,
    totalUnavailableSeconds: 0,
    totalGeneratorSeconds: null,
    totalSeconds: 0,
  }),
  getOutageSchedule: async () => ({
    days: [],
    updatedOn: "2026-01-01T00:00:00Z",
  }),
  registerDevice: async (body: unknown) => body,
  getDevice: async () => ({ id: "id" }),
  updateSubscriptions: async () => ({ id: "id" }),
  unregisterDevice: async () => ({ success: true }),
  getPushTopics: async () => [],
  getHealth: async () => ({ status: "ok" as const }),
  getReadiness: async () => ({
    status: "ready" as const,
    checks: { mongodb: "healthy", redis: "healthy" },
  }),
};
const snapshot = {
  getOutageSchedule: () => null,
  getSnapshot: () => null,
  isStale: () => true,
  health: () => ({
    status: "unhealthy",
    localEpoch: 0,
    localVersion: 0,
    versionLag: 0,
    snapshotAgeSeconds: null,
  }),
  stop: async () => undefined,
};

let server: ReturnType<typeof request>;
let app: INestApplication;

before(async () => {
  process.env.APP_ACCESS_TOKEN = "mobile-token";
  process.env.API_DOCS_ENABLED = "true";
  process.env.NODE_ENV = "test";
  process.env.APP_LOG_LEVEL = "silent";
  process.env.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = "false";
  process.env.FEATURE_DASHBOARD_SNAPSHOT_PUBLISH = "false";
  process.env.FEATURE_DEYE_POLLING_PROCESSING = "false";
  const throttleCounts = new Map<string, number>();
  const redis = {
    ping: async () => "PONG",
    quit: async () => "OK",
    eval: async (
      _script: string,
      options: { keys: string[]; arguments: string[] },
    ) => {
      const key = options.keys[0];
      const hits = (throttleCounts.get(key) ?? 0) + 1;
      throttleCounts.set(key, hits);
      const blocked = hits > Number(options.arguments[1]);
      return [
        hits,
        60_000,
        blocked ? 1 : 0,
        blocked ? Number(options.arguments[2]) : 0,
      ];
    },
  };
  const moduleRef = await Test.createTestingModule({ imports: [AppModule] })
    .overrideProvider(INTERNAL_API)
    .useValue(api)
    .overrideProvider(REDIS_READER)
    .useValue(redis)
    .overrideProvider(REDIS_SUBSCRIBER)
    .useValue(redis)
    .overrideProvider(SNAPSHOT_CLIENT)
    .useValue(snapshot)
    .compile();
  const nestApp = moduleRef.createNestApplication();
  setupOpenApi(nestApp, moduleRef.get(appConfig.KEY));
  nestApp.useGlobalPipes(createValidationPipe());
  await nestApp.init();
  app = nestApp;
  server = request(nestApp.getHttpServer());
});

after(async () => {
  await app.close();
});

test("public route requires the existing app token and preserves config shape", async () => {
  await server
    .get("/api/dashboard/config")
    .expect(401)
    .expect({ detail: "Invalid app token" });
  await server
    .get("/api/dashboard/config")
    .set("X-App-Token", "mobile-token")
    .expect(200)
    .expect({
      title: { uk: "Панель" },
      enableOutagesSchedule: true,
      outagesScheduleQueue: "1.1",
    });
});

test("summary validation status remains available", async () => {
  await server
    .post("/api/dashboard/buildings/summary")
    .set("X-App-Token", "mobile-token")
    .send({ buildingIds: ["bad"] })
    .expect(422);
});

test("invalid power-log date ranges retain the 400 response", async () => {
  await server
    .post("/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs")
    .set("X-App-Token", "mobile-token")
    .send({
      startDate: "2026-01-02T00:00:00Z",
      endDate: "2026-01-01T00:00:00Z",
    })
    .expect(400)
    .expect({ detail: "startDate must be before endDate" });
});

test("missing power-log dates retain the legacy 400 response", async () => {
  await server
    .post("/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs")
    .set("X-App-Token", "mobile-token")
    .send({})
    .expect(400)
    .expect({ detail: "Invalid date format" });
});

test("snapshot health reporting remains available", async () => {
  await server
    .get("/health/dashboard-snapshot")
    .set("X-App-Token", "mobile-token")
    .expect(200)
    .expect((response) => {
      assert.equal(response.body.component, "dashboard_snapshot");
      assert.equal(response.body.status, "disabled");
    });
});

test("all dashboard, outage, and push routes remain wired to the internal API", async () => {
  const headers = { "X-App-Token": "mobile-token" };
  const id = "507f1f77bcf86cd799439011";
  const dateRange = {
    startDate: "2026-01-01T00:00:00Z",
    endDate: "2026-01-02T00:00:00Z",
  };

  await server.get("/api/dashboard/buildings").set(headers).expect(200);
  await server
    .post("/api/dashboard/buildings/summary")
    .set(headers)
    .send({ buildingIds: [id] })
    .expect(200);
  await server.get("/api/dashboard/config").set(headers).expect(200);
  await server
    .post(`/api/dashboard/buildings/${id}/power-logs`)
    .set(headers)
    .send(dateRange)
    .expect(200);
  await server
    .get("/api/outagesSchedule/outagesSchedule/1.1")
    .set(headers)
    .expect(200);
  await server
    .post("/api/push/devices")
    .set(headers)
    .send({ token: "device-token", platform: "android" })
    .expect(200);
  await server
    .post("/api/push/devices/current")
    .set(headers)
    .send({ token: "device-token" })
    .expect(200);
  await server
    .post("/api/push/devices/subscriptions")
    .set(headers)
    .send({ token: "device-token" })
    .expect(200);
  await server
    .post("/api/push/devices/unregister")
    .set(headers)
    .send({ token: "device-token" })
    .expect(200);
  await server.get("/api/push/topics").set(headers).expect(200);

  api.getDevice = async () => {
    throw new InternalApiError(
      "Internal API request failed with status 404",
      404,
      "Device not registered",
    );
  };
  await server
    .post("/api/push/devices/current")
    .set(headers)
    .send({ token: "unknown" })
    .expect(404)
    .expect({ detail: "Device not registered" });
});

test("health probes are reachable without the mobile app token", async () => {
  await server
    .get("/health/live")
    .set("X-Request-Id", "probe-test-123")
    .expect(200)
    .expect("X-Request-Id", "probe-test-123")
    .expect((response) => {
      assert.equal(response.body.status, "alive");
    });
  await server
    .get("/health/ready")
    .expect(200)
    .expect((response) => {
      assert.equal(response.body.status, "ready");
    });
});

test("development OpenAPI documents public routes and app-token security", async () => {
  await server
    .get("/docs/openapi.json")
    .expect(200)
    .expect((response) => {
      assert.ok(response.body.paths["/api/dashboard/buildings"]);
      assert.ok(response.body.paths["/api/push/devices"]);
      assert.ok(response.body.components.securitySchemes["app-token"]);
    });
});

test("detailed health requires the app token while probes stay public", async () => {
  await server.get("/health").expect(401);
  await server.get("/health/dashboard-snapshot").expect(401);
  await server.get("/health/redis-dashboard").expect(401);
  await server
    .get("/health/redis-dashboard")
    .set("X-App-Token", "mobile-token")
    .expect(200)
    .expect({ status: "disabled" });
  await server
    .get("/metrics")
    .set("X-App-Token", "mobile-token")
    .expect(404)
    .expect({ detail: "Not Found" });
});

test("readiness depends on the internal API but not on the back-end database", async () => {
  const original = api.getHealth;
  api.getHealth = async () => {
    throw new InternalApiError("down", 503, undefined);
  };
  await server
    .get("/health/ready")
    .expect(503)
    .expect((response) => {
      assert.equal(response.body.status, "not_ready");
      assert.deepEqual(response.body.checks, {
        redis: "healthy",
        internalApi: "unhealthy",
      });
    });
  api.getHealth = original;
});

test("invalid building ids return the FastAPI-shaped 422 detail", async () => {
  await server
    .post("/api/dashboard/buildings/not-an-object-id/power-logs")
    .set("X-App-Token", "mobile-token")
    .send({
      startDate: "2026-01-01T00:00:00Z",
      endDate: "2026-01-02T00:00:00Z",
    })
    .expect(422)
    .expect((response) => {
      assert.ok(Array.isArray(response.body.detail));
      assert.deepEqual(response.body.detail[0].loc, ["path", "building_id"]);
    });
});

test("power-log dates follow the legacy ISO 8601 rules", async () => {
  const headers = { "X-App-Token": "mobile-token" };
  const path = "/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs";
  for (const startDate of ["Jan 1 2026", "2026-02-30T00:00:00Z", "2026"]) {
    await server
      .post(path)
      .set(headers)
      .send({ startDate, endDate: "2026-03-02T00:00:00Z" })
      .expect(400)
      .expect({ detail: "Invalid date format" });
  }
  // Naive timestamps are UTC, offsets are honoured, and snake_case is accepted.
  await server
    .post(path)
    .set(headers)
    .send({
      start_date: "2026-01-01T01:30:00+02:00",
      end_date: "2026-01-01T00:00:00",
    })
    .expect(200);
  await server
    .post(path)
    .set(headers)
    .send({
      startDate: "2026-01-01T03:00:00+02:00",
      endDate: "2026-01-01T00:30:00",
    })
    .expect(400)
    .expect({ detail: "startDate must be before endDate" });
});

test("snake_case request fields from Pydantic aliases are still accepted", async () => {
  const headers = { "X-App-Token": "mobile-token" };
  let summaryIds: string[] = [];
  let subscriptions: unknown;
  let registration: unknown;
  const originals = {
    getBuildingSummaries: api.getBuildingSummaries,
    updateSubscriptions: api.updateSubscriptions,
    registerDevice: api.registerDevice,
  };
  api.getBuildingSummaries = async (ids?: unknown) => {
    summaryIds = ids as string[];
    return [];
  };
  api.updateSubscriptions = async (body?: unknown) => {
    subscriptions = body;
    return { id: "id" };
  };
  api.registerDevice = async (body: unknown) => {
    registration = body;
    return body;
  };

  await server
    .post("/api/dashboard/buildings/summary")
    .set(headers)
    .send({ building_ids: ["507f1f77bcf86cd799439011"] })
    .expect(200);
  await server
    .post("/api/push/devices/subscriptions")
    .set(headers)
    .send({ token: "t", disabled_topics: ["outages"] })
    .expect(200);
  await server
    .post("/api/push/devices/subscriptions")
    .set(headers)
    .send({ token: "t2" })
    .expect(200);
  const defaults = subscriptions;
  await server
    .post("/api/push/devices")
    .set(headers)
    .send({ token: "t3", platform: "android", app_version: "1.2.3" })
    .expect(200);

  assert.deepEqual(summaryIds, ["507f1f77bcf86cd799439011"]);
  const plain = (value: unknown) => JSON.parse(JSON.stringify(value));
  assert.deepEqual(plain(defaults), {
    token: "t2",
    enabled: true,
    disabledTopics: [],
    buildings: [],
  });
  assert.deepEqual(plain(registration), {
    token: "t3",
    platform: "android",
    language: "uk",
    appVersion: "1.2.3",
  });
  Object.assign(api, originals);
});

test("missing outage schedules keep the legacy 404 message", async () => {
  const original = api.getOutageSchedule;
  api.getOutageSchedule = async () => {
    throw new InternalApiError("not found", 404, "Schedule not found");
  };
  await server
    .get("/api/outagesSchedule/outagesSchedule/9.9")
    .set("X-App-Token", "mobile-token")
    .expect(404)
    .expect({ detail: "No schedule found for queue 9.9" });
  api.getOutageSchedule = original;
});

// Runs last: it exhausts the registration rate limit for this client.
test("push registration rate limit returns 429 after the configured burst", async () => {
  const headers = { "X-App-Token": "mobile-token" };
  const statuses: number[] = [];
  // Earlier tests already used part of the 8-per-minute budget.
  for (let attempt = 0; attempt < 9; attempt += 1) {
    const response = await server
      .post("/api/push/devices")
      .set(headers)
      .send({ token: `device-${attempt}`, platform: "android" });
    statuses.push(response.status);
  }
  const firstBlocked = statuses.indexOf(429);
  assert.ok(firstBlocked > 0, `expected a 429, got ${statuses.join(",")}`);
  assert.ok(statuses.slice(0, firstBlocked).every((status) => status === 200));
  assert.ok(statuses.slice(firstBlocked).every((status) => status === 429));
});
