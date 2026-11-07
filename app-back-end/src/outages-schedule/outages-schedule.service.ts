import { Inject, Injectable } from "@nestjs/common";
import { InternalApiClient } from "../../../shared/typescript/src/index.js";
import { SnapshotService } from "../snapshots/snapshot.service.js";
import { INTERNAL_API } from "../tokens.js";

@Injectable()
export class OutagesScheduleService {
  constructor(
    @Inject(INTERNAL_API) private readonly api: InternalApiClient,
    private readonly snapshots: SnapshotService,
  ) {}

  getSchedule(queue: string) {
    return (
      this.snapshots.getOutageSchedule(queue) ??
      this.api.getOutageSchedule(queue)
    );
  }
}
