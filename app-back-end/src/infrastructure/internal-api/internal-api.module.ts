import { Module } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { InternalApiClient } from "../../shared.js";
import { appConfig } from "../../config/app.config.js";
import { INTERNAL_API } from "../../tokens.js";

@Module({
  providers: [
    {
      provide: INTERNAL_API,
      inject: [appConfig.KEY],
      useFactory: (config: ConfigType<typeof appConfig>) =>
        new InternalApiClient(
          config.internalApiUrl,
          config.internalApiToken,
          config.internalApiTimeoutMs,
        ),
    },
  ],
  exports: [INTERNAL_API],
})
export class InternalApiModule {}
