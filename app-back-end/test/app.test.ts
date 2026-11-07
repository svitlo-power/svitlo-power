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
import { InternalApiError } from "../../shared/typescript/src/index.js";

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
  getBuildingsWithSummary: async () => [],
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
  health: () => ({ status: "unhealthy" }),
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

test("public route requires the existing app token and preserves aliased config shape", async () => {
  await server
    .get("/api/dashboard/config")
    .expect(401)
    .expect({ detail: "Invalid app token" });
  await server
    .get("/api/buildings/dashboardConfig")
    .set("X-App-Token", "mobile-token")
    .expect(200)
    .expect({
      title: { uk: "Панель" },
      enableOutagesSchedule: true,
      outagesScheduleQueue: "1.1",
    });
});

test("legacy route aliases and validation status remain available", async () => {
  await server
    .get("/api/buildings/buildings")
    .set("X-App-Token", "mobile-token")
    .expect(200);
  await server
    .post("/api/dashboard/buildings/summary")
    .set("X-App-Token", "mobile-token")
    .send({ buildingIds: ["bad"] })
    .expect(422);
});

test("invalid power-log date ranges retain the 400 response", async () => {
  await server
    .post("/api/buildings/507f1f77bcf86cd799439011/power-logs")
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
    .post("/api/buildings/507f1f77bcf86cd799439011/power-logs")
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
      assert.equal(response.body.status, "unhealthy");
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
  await server
    .get("/api/dashboard/buildings-with-summary")
    .set(headers)
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

test("push registration rate limit returns 429 after the configured burst", async () => {
  const headers = { "X-App-Token": "mobile-token" };
  for (let attempt = 0; attempt < 7; attempt += 1) {
    await server
      .post("/api/push/devices")
      .set(headers)
      .send({ token: `device-${attempt}`, platform: "android" })
      .expect(200);
  }
  await server
    .post("/api/push/devices")
    .set(headers)
    .send({ token: "rate-limited-device", platform: "android" })
    .expect(429);
});
