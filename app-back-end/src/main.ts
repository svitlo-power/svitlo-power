import "reflect-metadata";
import { ConfigType } from "@nestjs/config";
import { NestFactory } from "@nestjs/core";
import helmet from "helmet";
import { Logger } from "nestjs-pino";
import { appConfig } from "./config/app.config.js";
import { setupOpenApi } from "./http/openapi.js";
import { createValidationPipe } from "./http/validation.pipe.js";
import { createMetricsServer } from "./metrics/metrics.server.js";
import { MetricsService } from "./metrics/metrics.service.js";
import { SnapshotService } from "./snapshots/snapshot.service.js";
import { AppModule } from "./app.module.js";

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  app.useGlobalPipes(createValidationPipe());
  app.enableShutdownHooks();
  app.useLogger(app.get(Logger));
  const config = app.get<ConfigType<typeof appConfig>>(appConfig.KEY);
  app.use(
    helmet({
      contentSecurityPolicy: config.apiDocsEnabled ? false : undefined,
    }),
  );
  app.getHttpAdapter().getInstance().set("trust proxy", config.trustProxyHops);
  setupOpenApi(app, config);

  const metricsServer = createMetricsServer(
    app.get(MetricsService),
    app.get(SnapshotService),
  );
  await app.listen(config.port, "0.0.0.0");
  metricsServer.listen(config.metricsPort, "0.0.0.0");
  const closeMetrics = () => metricsServer.close();
  process.once("SIGTERM", closeMetrics);
  process.once("SIGINT", closeMetrics);
}

void bootstrap();
