import { Inject, Injectable } from "@nestjs/common";
import { RedisConnections } from "../infrastructure/redis/redis-connections.service.js";
import { InternalApiClient } from "../shared.js";
import { SnapshotService } from "../snapshots/snapshot.service.js";
import { INTERNAL_API } from "../tokens.js";

type CheckStatus = "healthy" | "unhealthy";

@Injectable()
export class HealthService {
  constructor(
    private readonly redis: RedisConnections,
    private readonly snapshots: SnapshotService,
    @Inject(INTERNAL_API) private readonly api: InternalApiClient,
  ) {}

  async health() {
    const { redis, internalApi } = await this.dependencyChecks();
    const snapshot = this.snapshots.health();
    const checks = {
      redis: { status: redis, component: "redis" },
      internalApi: { status: internalApi, component: "internal_api" },
      dashboard_snapshot: {
        status: this.snapshots.isEnabled() ? snapshot.status : "disabled",
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
      status: this.snapshots.isEnabled() ? snapshot.status : "disabled",
      component: "dashboard_snapshot",
      details: {
        epoch: snapshot.localEpoch,
        version: snapshot.localVersion,
        age_seconds: snapshot.snapshotAgeSeconds,
      },
      timestamp: new Date().toISOString(),
    };
  }

  /**
   * Ready means this service can answer requests: its own Redis is reachable
   * and the internal API accepts our credentials. The back-end's database
   * health is deliberately not included, so a Mongo incident does not mark
   * every consumer unhealthy and trigger cascading restarts.
   */
  async readiness() {
    const checks = await this.dependencyChecks();
    const ready = Object.values(checks).every((status) => status === "healthy");
    return { status: ready ? "ready" : "not_ready", checks };
  }

  redisDashboardHealth() {
    return this.snapshots.isEnabled()
      ? this.snapshots.health()
      : { status: "disabled" as const };
  }

  private async dependencyChecks(): Promise<{
    redis: CheckStatus;
    internalApi: CheckStatus;
  }> {
    const [redis, internalApi] = await Promise.all([
      this.redis.ping(),
      this.api.getHealth().then(
        () => true,
        () => false,
      ),
    ]);
    return {
      redis: redis ? "healthy" : "unhealthy",
      internalApi: internalApi ? "healthy" : "unhealthy",
    };
  }
}
