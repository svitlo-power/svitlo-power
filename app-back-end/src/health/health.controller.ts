import { Controller, Get, Res } from "@nestjs/common";
import { SkipThrottle } from "@nestjs/throttler";
import { Response } from "express";
import { HealthService } from "./health.service.js";

/**
 * Only /health/live and /health/ready are exempt from the app token (see
 * AppTokenGuard) so container probes work. Detailed health exposes internal
 * state and keeps requiring the token, as in the Python service.
 */
@Controller("health")
@SkipThrottle()
export class HealthController {
  constructor(private readonly health: HealthService) {}

  @Get("live")
  liveness() {
    return { status: "alive", timestamp: Date.now() / 1000 };
  }

  @Get("ready")
  async readiness(@Res({ passthrough: true }) response: Response) {
    const result = await this.health.readiness();
    if (result.status !== "ready") response.status(503);
    return { ...result, timestamp: Date.now() / 1000 };
  }

  @Get()
  getHealth() {
    return this.health.health();
  }

  @Get("dashboard-snapshot")
  dashboardSnapshotHealth() {
    return this.health.dashboardSnapshotHealth();
  }

  @Get("redis-dashboard")
  redisDashboardHealth(@Res({ passthrough: true }) response: Response) {
    const result = this.health.redisDashboardHealth();
    if (result.status !== "disabled" && result.status !== "healthy")
      response.status(503);
    return result;
  }
}
