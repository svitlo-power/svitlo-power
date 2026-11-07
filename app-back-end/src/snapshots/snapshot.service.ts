import {
  Inject,
  Injectable,
  OnModuleDestroy,
  OnModuleInit,
} from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import {
  DashboardSnapshotClient,
  DashboardSnapshotHealth,
} from "../../../shared/typescript/src/index.js";
import { appConfig } from "../config/app.config.js";
import { SNAPSHOT_CLIENT } from "../tokens.js";

@Injectable()
export class SnapshotService implements OnModuleInit, OnModuleDestroy {
  constructor(
    @Inject(SNAPSHOT_CLIENT) private readonly client: DashboardSnapshotClient,
    @Inject(appConfig.KEY)
    private readonly config: ConfigType<typeof appConfig>,
  ) {}

  async onModuleInit(): Promise<void> {
    if (this.config.snapshotReadsEnabled) await this.client.start();
  }

  async onModuleDestroy(): Promise<void> {
    await this.client.stop();
  }

  isEnabled(): boolean {
    return this.config.snapshotReadsEnabled;
  }

  getActiveSnapshot() {
    if (!this.isEnabled() || this.client.isStale()) return null;
    return this.client.getSnapshot();
  }

  getOutageSchedule(queue: string) {
    return this.getActiveSnapshot()
      ? this.client.getOutageSchedule(queue)
      : null;
  }

  health(): DashboardSnapshotHealth {
    return this.client.health();
  }
}
