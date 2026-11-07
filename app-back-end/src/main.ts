import "reflect-metadata";
import { ConfigType } from "@nestjs/config";
import { NestFactory } from "@nestjs/core";
import helmet from "helmet";
import { Logger } from "nestjs-pino";
import { appConfig } from "./config/app.config.js";
import { setupOpenApi } from "./http/openapi.js";
import { createValidationPipe } from "./http/validation.pipe.js";
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
  const port = config.port;
  const metricsPort = config.metricsPort;
  await app.listen(port, "0.0.0.0");
  const metricsServer = app
    .getHttpAdapter()
    .getInstance()
    .listen(metricsPort, "0.0.0.0");
  process.once("SIGTERM", () => metricsServer.close());
  process.once("SIGINT", () => metricsServer.close());
}

void bootstrap();
