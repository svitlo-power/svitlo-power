import { Controller, Get, Param } from "@nestjs/common";
import { ApiOperation, ApiSecurity, ApiTags } from "@nestjs/swagger";
import { OutagesScheduleService } from "./outages-schedule.service.js";

@Controller("api")
@ApiTags("outages")
@ApiSecurity("app-token")
export class OutagesScheduleController {
  constructor(private readonly schedules: OutagesScheduleService) {}

  @Get("outagesSchedule/outagesSchedule/:queue")
  @ApiOperation({ summary: "Get the outage schedule for a queue" })
  getSchedule(@Param("queue") queue: string) {
    return this.schedules.getSchedule(queue);
  }
}
