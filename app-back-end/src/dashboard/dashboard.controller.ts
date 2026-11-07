import { Body, Controller, Get, HttpCode, Param, Post } from "@nestjs/common";
import { ApiOperation, ApiSecurity, ApiTags } from "@nestjs/swagger";
import { BuildingIdsDto, PowerLogsDto } from "./dashboard.dto.js";
import { DashboardService } from "./dashboard.service.js";

@Controller("api")
@ApiTags("dashboard")
@ApiSecurity("app-token")
export class DashboardController {
  constructor(private readonly dashboard: DashboardService) {}

  @Get("dashboard/buildings")
  @ApiOperation({ summary: "List public buildings" })
  getBuildings() {
    return this.dashboard.getBuildings();
  }

  @HttpCode(200)
  @Post("dashboard/buildings/summary")
  @ApiOperation({ summary: "Get summaries for selected buildings" })
  getBuildingSummaries(@Body() body: BuildingIdsDto) {
    return this.dashboard.getBuildingSummaries(body);
  }

  @Get(["buildings/buildings", "dashboard/buildings-with-summary"])
  @ApiOperation({ summary: "Get buildings with their current summaries" })
  getBuildingsWithSummary() {
    return this.dashboard.getBuildingsWithSummary();
  }

  @Get(["dashboard/config", "buildings/dashboardConfig"])
  @ApiOperation({ summary: "Get mobile dashboard configuration" })
  getDashboardConfig() {
    return this.dashboard.getDashboardConfig();
  }

  @HttpCode(200)
  @Post([
    "dashboard/buildings/:building_id/power-logs",
    "buildings/:building_id/power-logs",
  ])
  @ApiOperation({ summary: "Get power availability logs for a building" })
  getPowerLogs(
    @Param("building_id") buildingId: string,
    @Body() body: PowerLogsDto,
  ) {
    return this.dashboard.getPowerLogs(buildingId, body);
  }
}
