import { Module } from "@nestjs/common";
import { ProcessingModule } from "../processing/processing.module.js";
import { RefreshController } from "./refresh.controller.js";
import { RefreshCoordinator } from "./refresh-coordinator.service.js";

@Module({
  imports: [ProcessingModule],
  controllers: [RefreshController],
  providers: [RefreshCoordinator],
  exports: [RefreshCoordinator],
})
export class TriggersModule {}
