import { Module } from "@nestjs/common";
import { InternalApiModule } from "../infrastructure/internal-api/internal-api.module.js";
import { SnapshotModule } from "../snapshots/snapshot.module.js";
import { OutagesScheduleController } from "./outages-schedule.controller.js";
import { OutagesScheduleService } from "./outages-schedule.service.js";

@Module({
  imports: [InternalApiModule, SnapshotModule],
  controllers: [OutagesScheduleController],
  providers: [OutagesScheduleService],
})
export class OutagesScheduleModule {}
