import { Injectable } from "@nestjs/common";
import {
  aggregateReadinessStatus,
  CheckStatus,
  toCheckStatus,
} from "@svitlo-power/shared-typescript";
import { RedisConnections } from "../infrastructure/redis/redis-connections.service.js";
import { ProcessingService } from "../processing/processing.service.js";

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
    return { status: aggregateReadinessStatus(checks), checks };
  }

  private async redisStatus(): Promise<CheckStatus> {
    return toCheckStatus(await this.redis.ping());
  }
}
