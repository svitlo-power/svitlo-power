import { Inject, Injectable } from "@nestjs/common";
import { InternalApiClient } from "../shared.js";
import { INTERNAL_API } from "../tokens.js";
import { DeviceRegistrationDto, DeviceSubscriptionsDto } from "./push.dto.js";

@Injectable()
export class PushService {
  constructor(@Inject(INTERNAL_API) private readonly api: InternalApiClient) {}

  registerDevice(body: DeviceRegistrationDto) {
    return this.api.registerDevice(body);
  }

  getDevice(token: string) {
    return this.api.getDevice(token);
  }

  updateSubscriptions(body: DeviceSubscriptionsDto) {
    return this.api.updateSubscriptions(body);
  }

  unregisterDevice(token: string) {
    return this.api.unregisterDevice(token);
  }

  getTopics() {
    return this.api.getPushTopics();
  }
}
