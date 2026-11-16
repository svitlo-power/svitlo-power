import { Module } from "@nestjs/common";
import { MetricsService } from "./metrics.service.js";

@Module({
  providers: [MetricsService],
  exports: [MetricsService],
})
export class MetricsModule {}
