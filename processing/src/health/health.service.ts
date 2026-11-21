import { Injectable } from "@nestjs/common";
import { RedisConnections } from "../infrastructure/redis/redis-connections.service.js";
import { ProcessingService } from "../processing/processing.service.js";

type CheckStatus = "healthy" | "unhealthy";

@Injectable()
export class HealthService {
  constructor(
    private readonly redis: RedisConnections,
    private readonly processing: ProcessingService,
  ) {}

  async health() {
    const checks = {
      redis: { status: await this.redisStatus(), component: "redis" },
      snapshot: {
        status: this.processing.status(),
        component: "snapshot",
        details: this.processing.details(),
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

  async readiness() {
    const checks = {
      redis: await this.redisStatus(),
      snapshot: this.processing.status(),
    };
    const ready = Object.values(checks).every((status) => status === "healthy");
    return { status: ready ? "ready" : "not_ready", checks };
  }

  private async redisStatus(): Promise<CheckStatus> {
    return (await this.redis.ping()) ? "healthy" : "unhealthy";
  }
}
