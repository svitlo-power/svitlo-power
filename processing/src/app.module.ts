import { Module } from "@nestjs/common";
import { ConfigModule } from "@nestjs/config";
import { APP_GUARD } from "@nestjs/core";
import { LoggerModule } from "nestjs-pino";
import { ConfigType } from "@nestjs/config";
import { randomUUID } from "node:crypto";
import {
  processingConfig,
  validateEnvironment,
} from "./config/processing.config.js";
import { HealthModule } from "./health/health.module.js";
import { InternalTokenGuard } from "./http/internal-token.guard.js";
import { MetricsModule } from "./metrics/metrics.module.js";
import { ProcessingModule } from "./processing/processing.module.js";
import { SchedulerModule } from "./scheduler/scheduler.module.js";
import { TriggersModule } from "./triggers/triggers.module.js";

/**
 * Root application module.
 *
 * `DatabaseModule` and `RedisModule` are imported by the modules that need
 * them, so tests can compose a subset without opening real connections.
 */
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      ignoreEnvFile: process.env.NODE_ENV === "production",
      envFilePath: process.env.ENV_FILE ?? "../.env",
      validate: validateEnvironment,
      load: [processingConfig],
    }),
    LoggerModule.forRootAsync({
      inject: [processingConfig.KEY],
      useFactory: (config: ConfigType<typeof processingConfig>) => ({
        pinoHttp: {
          level: config.logLevel,
          genReqId: (request, response) => {
            const supplied = request.headers["x-request-id"];
            const requestId =
              typeof supplied === "string" &&
              /^[a-zA-Z0-9._:-]{1,128}$/.test(supplied)
                ? supplied
                : randomUUID();
            response.setHeader("X-Request-Id", requestId);
            return requestId;
          },
          redact: {
            paths: [
              "req.headers.authorization",
              "req.headers.x-request-id",
              "req.body.token",
            ],
            remove: true,
          },
          customProps: () => ({ service: "processing" }),
          transport: config.prettyLogs
            ? {
                target: "pino-pretty",
                options: { colorize: true, singleLine: true },
              }
            : undefined,
        },
      }),
    }),
    MetricsModule,
    ProcessingModule,
    SchedulerModule,
    TriggersModule,
    HealthModule,
  ],
  providers: [{ provide: APP_GUARD, useClass: InternalTokenGuard }],
})
export class AppModule {}
