import { Inject, Injectable, Logger } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { processingConfig } from "../config/processing.config.js";
import {
  ProcessingService,
  ReconcileResult,
} from "../processing/processing.service.js";

/**
 * Coalesces refresh requests.
 *
 * A burst of triggers inside the debounce window produces a single build; every
 * caller receives the resulting snapshot coordinates, matching the legacy
 * producer's leader/follower behaviour.
 */
@Injectable()
export class RefreshCoordinator {
  private readonly logger = new Logger(RefreshCoordinator.name);
  private pending: Promise<ReconcileResult> | null = null;
  private debounceTimer: NodeJS.Timeout | null = null;
  private followers = 0;

  constructor(
    @Inject(processingConfig.KEY)
    private readonly config: ConfigType<typeof processingConfig>,
    private readonly processing: ProcessingService,
  ) {}

  async request(reason: string): Promise<ReconcileResult> {
    if (this.pending) {
      this.followers += 1;
      return this.pending;
    }

    this.pending = new Promise<ReconcileResult>((resolve) => {
      this.debounceTimer = setTimeout(() => {
        this.debounceTimer = null;
        void this.processing
          .reconcile(reason)
          .then(resolve)
          .finally(() => {
            if (this.followers > 0) {
              this.logger.log(
                `Coalesced ${this.followers} refresh request(s) into one build`,
              );
              this.followers = 0;
            }
            this.pending = null;
          });
      }, this.config.refreshCoalesceMs);
      this.debounceTimer.unref?.();
    });

    return this.pending;
  }

  /** Number of requests folded into the in-flight build. */
  get coalescedCount(): number {
    return this.followers;
  }
}
