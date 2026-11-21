import { createServer, Server } from "node:http";
import { MetricsService } from "./metrics.service.js";

/**
 * Serves only GET /metrics on the dedicated metrics port, so the application
 * API is never reachable through the Prometheus scrape port.
 */
export function createMetricsServer(metrics: MetricsService): Server {
  return createServer((request, response) => {
    const path = (request.url ?? "/").split("?")[0];
    if (request.method !== "GET" || path !== "/metrics") {
      response.writeHead(404, { "Content-Type": "application/json" });
      response.end(JSON.stringify({ detail: "Not Found" }));
      return;
    }
    metrics.registry.metrics().then(
      (body) => {
        response.writeHead(200, {
          "Content-Type": metrics.registry.contentType,
        });
        response.end(body);
      },
      () => {
        response.writeHead(500);
        response.end();
      },
    );
  });
}
