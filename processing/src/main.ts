import "reflect-metadata";
import { ConfigType } from "@nestjs/config";
import { NestFactory } from "@nestjs/core";
import { NestExpressApplication } from "@nestjs/platform-express";
import { Logger } from "nestjs-pino";
import { AppModule } from "./app.module.js";
import { processingConfig } from "./config/processing.config.js";
import { createMetricsServer } from "./metrics/metrics.server.js";
import { MetricsService } from "./metrics/metrics.service.js";

async function bootstrap(): Promise<void> {
  const app = await NestFactory.create<NestExpressApplication>(AppModule, {
    bufferLogs: true,
    bodyParser: false,
  });
  app.useBodyParser("json");
  app.enableShutdownHooks();
  app.useLogger(app.get(Logger));
  const config = app.get<ConfigType<typeof processingConfig>>(
    processingConfig.KEY,
  );

  const metricsServer = createMetricsServer(app.get(MetricsService));
  await app.listen(config.port, "0.0.0.0");
  metricsServer.listen(config.metricsPort, "0.0.0.0");
  const closeMetrics = () => metricsServer.close();
  process.once("SIGTERM", closeMetrics);
  process.once("SIGINT", closeMetrics);
}

void bootstrap();
