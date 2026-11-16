import { Module } from "@nestjs/common";
import { InternalApiModule } from "../infrastructure/internal-api/internal-api.module.js";
import { SnapshotModule } from "../snapshots/snapshot.module.js";
import { DashboardController } from "./dashboard.controller.js";
import { DashboardService } from "./dashboard.service.js";

@Module({
  imports: [InternalApiModule, SnapshotModule],
  controllers: [DashboardController],
  providers: [DashboardService],
})
export class DashboardModule {}
