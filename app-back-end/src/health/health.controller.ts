import { Controller, Get, Res } from "@nestjs/common";
import { SkipThrottle } from "@nestjs/throttler";
import { Response } from "express";
import { HealthService } from "./health.service.js";

@Controller()
@SkipThrottle()
export class HealthController {
  constructor(private readonly health: HealthService) {}

  @Get("health/live")
  liveness() {
    return { status: "alive", timestamp: Date.now() / 1000 };
  }

  @Get("health")
  getHealth() {
    return this.health.health();
  }

  @Get("health/dashboard-snapshot")
  dashboardSnapshotHealth() {
    return this.health.dashboardSnapshotHealth();
  }

  @Get("health/ready")
  async readiness(@Res({ passthrough: true }) response: Response) {
    const result = await this.health.readiness();
    if (result.status !== "ready") response.status(503);
    return { ...result, timestamp: Date.now() / 1000 };
  }

  @Get("health/redis-dashboard")
  async redisDashboardHealth(@Res({ passthrough: true }) response: Response) {
    const result = this.health.redisDashboardHealth();
    if (result.status !== "disabled" && result.status !== "healthy")
      response.status(503);
    return result;
  }

  @Get("metrics")
  async metrics(@Res() response: Response): Promise<void> {
    const result = await this.health.metrics();
    response.setHeader("Content-Type", result.contentType);
    response.send(result.body);
  }
}
