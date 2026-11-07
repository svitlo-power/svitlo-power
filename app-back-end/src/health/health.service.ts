import { Inject, Injectable } from "@nestjs/common";
import { Gauge, Registry, collectDefaultMetrics } from "@prometheus-io/client";
import { InternalApiClient } from "../../../shared/typescript/src/index.js";
import { RedisConnections } from "../infrastructure/redis/redis-connections.service.js";
import { SnapshotService } from "../snapshots/snapshot.service.js";
import { INTERNAL_API } from "../tokens.js";

const registry = new Registry();
collectDefaultMetrics({ register: registry });
const snapshotAge = new Gauge({
  name: "redis_snapshot_age_seconds",
  help: "Age of the app-back-end local dashboard snapshot",
  registers: [registry],
});
const snapshotVersionLag = new Gauge({
  name: "redis_snapshot_version_lag",
  help: "Number of snapshot versions the app-back-end consumer is behind Redis",
  registers: [registry],
});

@Injectable()
export class HealthService {
  constructor(
    private readonly redis: RedisConnections,
    private readonly snapshots: SnapshotService,
    @Inject(INTERNAL_API) private readonly api: InternalApiClient,
  ) {}

  async health() {
    const [redis, api] = await Promise.all([
      this.redis.ping(),
      this.api.getHealth().then(
        () => "healthy",
        () => "unhealthy",
      ),
    ]);
    const snapshot = this.snapshots.health();
    const checks = {
      redis: { status: redis ? "healthy" : "unhealthy", component: "redis" },
      internalApi: { status: api, component: "internal_api" },
      dashboard_snapshot: {
        status: snapshot.status,
        component: "dashboard_snapshot",
        details: {
          epoch: snapshot.localEpoch,
          version: snapshot.localVersion,
          age_seconds: snapshot.snapshotAgeSeconds,
        },
      },
    };
    return {
      status: Object.values(checks).some(
        (check) => check.status === "unhealthy",
      )
        ? "unhealthy"
        : "healthy",
      checks,
      timestamp: new Date().toISOString(),
    };
  }

  dashboardSnapshotHealth() {
    const snapshot = this.snapshots.health();
    return {
      status: snapshot.status,
      component: "dashboard_snapshot",
      details: {
        epoch: snapshot.localEpoch,
        version: snapshot.localVersion,
        age_seconds: snapshot.snapshotAgeSeconds,
      },
      timestamp: new Date().toISOString(),
    };
  }

  async readiness() {
    const [redis, upstream] = await Promise.all([
      this.redis.ping(),
      this.api.getReadiness().catch(() => null),
    ]);
    const upstreamReady = upstream?.status === "ready";
    const ready = redis && upstreamReady;
    return {
      status: ready ? "ready" : "not_ready",
      checks: {
        internalApi: upstreamReady ? "healthy" : "unhealthy",
        mongodb: upstream?.checks.mongodb ?? "unknown",
        redis:
          redis && upstream?.checks.redis === "healthy"
            ? "healthy"
            : "unhealthy",
      },
    };
  }

  redisDashboardHealth() {
    return this.snapshots.isEnabled()
      ? this.snapshots.health()
      : { status: "disabled" };
  }

  async metrics() {
    const snapshot = this.snapshots.health();
    snapshotAge.set(
      typeof snapshot.snapshotAgeSeconds === "number"
        ? snapshot.snapshotAgeSeconds
        : 0,
    );
    snapshotVersionLag.set(Number(snapshot.versionLag ?? 0));
    return {
      contentType: registry.contentType,
      body: await registry.metrics(),
    };
  }
}
