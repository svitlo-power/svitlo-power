import { Body, Controller, Get, HttpCode, Post } from "@nestjs/common";
import { ApiOperation, ApiSecurity, ApiTags } from "@nestjs/swagger";
import { Throttle } from "@nestjs/throttler";
import {
  DeviceRegistrationDto,
  DeviceSubscriptionsDto,
  DeviceTokenDto,
} from "./push.dto.js";
import { PushService } from "./push.service.js";

@Controller("api/push")
@ApiTags("push")
@ApiSecurity("app-token")
export class PushController {
  constructor(private readonly push: PushService) {}

  @HttpCode(200)
  @Throttle({ default: { limit: 8, ttl: 60_000, blockDuration: 300_000 } })
  @Post("devices")
  @ApiOperation({ summary: "Register or refresh a mobile device token" })
  registerDevice(@Body() body: DeviceRegistrationDto) {
    return this.push.registerDevice(body);
  }

  @HttpCode(200)
  @Throttle({ default: { limit: 30, ttl: 60_000, blockDuration: 300_000 } })
  @Post("devices/current")
  @ApiOperation({ summary: "Get the current device registration" })
  getDevice(@Body() body: DeviceTokenDto) {
    return this.push.getDevice(body.token);
  }

  @HttpCode(200)
  @Throttle({ default: { limit: 15, ttl: 60_000, blockDuration: 300_000 } })
  @Post("devices/subscriptions")
  @ApiOperation({ summary: "Update device topic and building subscriptions" })
  updateSubscriptions(@Body() body: DeviceSubscriptionsDto) {
    return this.push.updateSubscriptions(body);
  }

  @HttpCode(200)
  @Throttle({ default: { limit: 8, ttl: 60_000, blockDuration: 300_000 } })
  @Post("devices/unregister")
  @ApiOperation({ summary: "Unregister a mobile device token" })
  unregisterDevice(@Body() body: DeviceTokenDto) {
    return this.push.unregisterDevice(body.token);
  }

  @Get("topics")
  @ApiOperation({ summary: "List available push topics" })
  getTopics() {
    return this.push.getTopics();
  }
}
