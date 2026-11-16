import { Module } from "@nestjs/common";
import { InternalApiModule } from "../infrastructure/internal-api/internal-api.module.js";
import { PushController } from "./push.controller.js";
import { PushService } from "./push.service.js";

@Module({
  imports: [InternalApiModule],
  controllers: [PushController],
  providers: [PushService],
})
export class PushModule {}
