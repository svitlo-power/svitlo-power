import { Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { processingConfig } from "../config/processing.config.js";
import { LeaseModule } from "../lease/lease.module.js";
import { MetricsModule } from "../metrics/metrics.module.js";
import { ShadowModule } from "../shadow/shadow.module.js";
import { ShadowPublisher } from "../shadow/shadow-publisher.service.js";
import { SnapshotModule } from "../snapshot/snapshot.module.js";
import { SnapshotPublisher } from "../snapshot/snapshot-publisher.service.js";
import { ACTIVE_PUBLISHER } from "../tokens.js";
import { ProcessingService } from "./processing.service.js";

/**
 * Chooses the publisher the processing flow writes through.
 *
 * The choice is made from the publish flag, never from whether a provider was
 * injected: with `?` on the constructor parameter Nest still injects the
 * provider, so a shadow-mode deployment would otherwise write to the production
 * keys and stall the legacy producer.
 */
export function selectActivePublisher(
  config: ConfigType<typeof processingConfig>,
  shadow: ShadowPublisher,
  production: SnapshotPublisher,
): ShadowPublisher | SnapshotPublisher {
  return config.publishEnabled ? production : shadow;
}

@Module({
  imports: [LeaseModule, MetricsModule, ShadowModule, SnapshotModule],
  providers: [
    ProcessingService,
    {
      provide: ACTIVE_PUBLISHER,
      inject: [processingConfig.KEY, ShadowPublisher, SnapshotPublisher],
      useFactory: selectActivePublisher,
    },
  ],
  exports: [ProcessingService],
})
export class ProcessingModule {}
