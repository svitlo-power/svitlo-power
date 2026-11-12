import { Inject, Injectable, NotFoundException } from "@nestjs/common";
import {
  InternalApiClient,
  InternalApiError,
  OutageSchedule,
} from "../shared.js";
import { SnapshotService } from "../snapshots/snapshot.service.js";
import { INTERNAL_API } from "../tokens.js";

@Injectable()
export class OutagesScheduleService {
  constructor(
    @Inject(INTERNAL_API) private readonly api: InternalApiClient,
    private readonly snapshots: SnapshotService,
  ) {}

  async getSchedule(
    queue: string,
  ): Promise<OutageSchedule | Record<string, unknown>> {
    const cached = this.snapshots.getOutageSchedule(queue);
    if (cached) return cached;
    try {
      return await this.api.getOutageSchedule(queue);
    } catch (error) {
      if (error instanceof InternalApiError && error.status === 404) {
        // Keep the legacy mobile API message.
        throw new NotFoundException({
          detail: `No schedule found for queue ${queue}`,
        });
      }
      throw error;
    }
  }
}
