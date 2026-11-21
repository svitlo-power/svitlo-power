import { Controller, Get, Res } from "@nestjs/common";
import { Response } from "express";
import { HealthService } from "./health.service.js";

/**
 * Liveness and readiness stay unauthenticated so container probes work; the
 * detailed report exposes internal state and requires the shared service token.
 */
@Controller("health")
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
}
