import { Module } from "@nestjs/common";
import { ConfigModule, ConfigType } from "@nestjs/config";
import { APP_FILTER, APP_GUARD } from "@nestjs/core";
import { ThrottlerGuard, ThrottlerModule } from "@nestjs/throttler";
import { LoggerModule } from "nestjs-pino";
import { randomUUID } from "node:crypto";
import { RedisClientType } from "redis";
import { appConfig, validateEnvironment } from "./config/app.config.js";
import { DashboardModule } from "./dashboard/dashboard.module.js";
import { HealthModule } from "./health/health.module.js";
import { RedisModule } from "./infrastructure/redis/redis.module.js";
import { RedisThrottlerStorage } from "./infrastructure/redis/redis-throttler.storage.js";
import { OutagesScheduleModule } from "./outages-schedule/outages-schedule.module.js";
import { PushModule } from "./push/push.module.js";
import { ApiExceptionFilter } from "./http/api-exception.filter.js";
import { AppTokenGuard } from "./http/app-token.guard.js";
import { REDIS_READER } from "./tokens.js";

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      ignoreEnvFile: process.env.NODE_ENV === "production",
      envFilePath: process.env.ENV_FILE ?? "../.env",
      validate: validateEnvironment,
      load: [appConfig],
    }),
    LoggerModule.forRootAsync({
      inject: [appConfig.KEY],
      useFactory: (config: ConfigType<typeof appConfig>) => ({
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
              "req.headers.x-app-token",
              "req.headers.x-request-id",
              "req.body.token",
            ],
            remove: true,
          },
          customProps: () => ({ service: "app-back-end" }),
          transport: config.prettyLogs
            ? {
                target: "pino-pretty",
                options: { colorize: true, singleLine: true },
              }
            : undefined,
        },
      }),
    }),
    ThrottlerModule.forRootAsync({
      imports: [RedisModule],
      inject: [appConfig.KEY, REDIS_READER],
      useFactory: (
        config: ConfigType<typeof appConfig>,
        redis: RedisClientType,
      ) => ({
        throttlers: [
          {
            name: "default",
            ttl: config.rateLimitWindowMs,
            limit: config.rateLimitMax,
            blockDuration: config.rateLimitBlockMs,
          },
        ],
        storage: new RedisThrottlerStorage(redis),
      }),
    }),
    DashboardModule,
    OutagesScheduleModule,
    PushModule,
    HealthModule,
  ],
  providers: [
    { provide: APP_GUARD, useClass: AppTokenGuard },
    { provide: APP_GUARD, useClass: ThrottlerGuard },
    { provide: APP_FILTER, useClass: ApiExceptionFilter },
  ],
})
export class AppModule {}
