import { Body, Controller, Post } from "@nestjs/common";
import { IsIn, IsOptional, IsString, MaxLength } from "class-validator";
import { RefreshCoordinator } from "./refresh-coordinator.service.js";

const REFRESH_REASONS = [
  "cache-miss",
  "manual",
  "config-change",
  "buildings-change",
  "station-change",
  "outages-change",
  "startup",
  "scheduled",
] as const;

export class RefreshSnapshotRequestDto {
  @IsOptional()
  @IsString()
  @IsIn(REFRESH_REASONS)
  @MaxLength(64)
  reason?: string;

  @IsOptional()
  @IsString()
  @MaxLength(128)
  requestedBy?: string;
}

/**
 * Internal trigger endpoint.
 *
 * Mirrors `POST /internal/v1/snapshots/refresh` from the legacy producer so the
 * BFFs can point at Processing without a client change after cutover.
 */
@Controller("internal/v1/snapshots")
export class RefreshController {
  constructor(private readonly coordinator: RefreshCoordinator) {}

  @Post("refresh")
  async refresh(@Body() body: RefreshSnapshotRequestDto) {
    const reason = body.reason ?? "manual";
    // `coalesced` is part of the result: reading a counter after the await
    // races with the coordinator resetting it in its `finally` block.
    const result = await this.coordinator.request(reason, body.requestedBy);
    return {
      accepted: true,
      epoch: result.epoch,
      version: result.version,
      coalesced: result.coalesced,
    };
  }
}
