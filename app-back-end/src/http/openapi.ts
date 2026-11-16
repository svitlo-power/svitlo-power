import { INestApplication } from "@nestjs/common";
import { ConfigType } from "@nestjs/config";
import { DocumentBuilder, SwaggerModule } from "@nestjs/swagger";
import { appConfig } from "../config/app.config.js";

export function setupOpenApi(
  app: INestApplication,
  config: ConfigType<typeof appConfig>,
): void {
  if (!config.apiDocsEnabled) return;

  const documentConfig = new DocumentBuilder()
    .setTitle("SvitloPower Mobile API")
    .setDescription("Public mobile API provided by app-back-end")
    .setVersion("1.0.0")
    .addApiKey(
      { type: "apiKey", in: "header", name: "X-App-Token" },
      "app-token",
    )
    .build();
  const document = SwaggerModule.createDocument(app, documentConfig);
  SwaggerModule.setup("docs", app, document, {
    jsonDocumentUrl: "docs/openapi.json",
  });
}
