import { readFileSync } from "node:fs";
import { registerAs } from "@nestjs/config";

/**
 * The back-end bounds each domain call with INTERNAL_API_TIMEOUT_SECONDS; the
 * client waits a little longer so the upstream's own 504 reaches us first.
 */
const INTERNAL_API_TIMEOUT_MARGIN_MS = 2_000;

function readVersion(): string {
  if (process.env.APP_VERSION) return process.env.APP_VERSION;
  try {
    return readFileSync("/app/VERSION", "utf8").trim() || "0000.00.00";
  } catch {
    return "0000.00.00";
  }
}

export interface AppConfiguration {
  version: string;
  port: number;
  metricsPort: number;
  trustProxyHops: number;
  appAccessToken: string;
  internalApiUrl: string;
  internalApiToken: string;
  internalApiTimeoutMs: number;
  redisUrl: string;
  snapshotRefreshUrl: string;
  snapshotStaleThresholdSeconds: number;
  snapshotReadsEnabled: boolean;
  apiDocsEnabled: boolean;
  logLevel: string;
  prettyLogs: boolean;
  rateLimitWindowMs: number;
  rateLimitMax: number;
  rateLimitBlockMs: number;
}

function integerSetting(
  env: Record<string, unknown>,
  key: string,
  fallback: number,
  minimum: number,
): string {
  const parsed = Number(env[key] ?? fallback);
  if (!Number.isSafeInteger(parsed) || parsed < minimum) {
    throw new Error(`${key} must be an integer >= ${minimum}`);
  }
  return String(parsed);
}

const positiveInteger = (
  env: Record<string, unknown>,
  key: string,
  fallback: number,
) => integerSetting(env, key, fallback, 1);

export function validateEnvironment(
  env: Record<string, unknown>,
): Record<string, unknown> {
  const logLevel = String(env.APP_LOG_LEVEL ?? "info");
  if (
    !["trace", "debug", "info", "warn", "error", "fatal", "silent"].includes(
      logLevel,
    )
  ) {
    throw new Error("APP_LOG_LEVEL must be a valid Pino level");
  }
  return {
    ...env,
    PORT: positiveInteger(env, "PORT", 8000),
    METRICS_PORT: positiveInteger(env, "METRICS_PORT", 9097),
    TRUST_PROXY_HOPS: integerSetting(env, "TRUST_PROXY_HOPS", 1, 0),
    INTERNAL_API_TIMEOUT_SECONDS: positiveInteger(
      env,
      "INTERNAL_API_TIMEOUT_SECONDS",
      10,
    ),
    APP_BACKEND_REDIS_DASHBOARD_STALE_THRESHOLD_SECONDS: positiveInteger(
      env,
      "APP_BACKEND_REDIS_DASHBOARD_STALE_THRESHOLD_SECONDS",
      300,
    ),
    APP_RATE_LIMIT_WINDOW_MS: positiveInteger(
      env,
      "APP_RATE_LIMIT_WINDOW_MS",
      60_000,
    ),
    APP_RATE_LIMIT_MAX: positiveInteger(env, "APP_RATE_LIMIT_MAX", 120),
    APP_RATE_LIMIT_BLOCK_MS: positiveInteger(
      env,
      "APP_RATE_LIMIT_BLOCK_MS",
      60_000,
    ),
    APP_LOG_LEVEL: logLevel,
  };
}

export const appConfig = registerAs("app", (): AppConfiguration => ({
  version: readVersion(),
  port: Number(process.env.PORT ?? 8000),
  metricsPort: Number(process.env.METRICS_PORT ?? 9097),
  trustProxyHops: Number(process.env.TRUST_PROXY_HOPS ?? 1),
  appAccessToken: process.env.APP_ACCESS_TOKEN ?? "",
  internalApiUrl:
    process.env.INTERNAL_API_URL ??
    "http://svitlo-power-back-end:5005/internal/v1/app",
  internalApiToken: process.env.INTERNAL_API_TOKEN ?? "",
  internalApiTimeoutMs:
    Number(process.env.INTERNAL_API_TIMEOUT_SECONDS ?? 10) * 1000 +
    INTERNAL_API_TIMEOUT_MARGIN_MS,
  redisUrl: process.env.REDIS_URI ?? "redis://svitlo-power-rds:6379/0",
  snapshotRefreshUrl:
    process.env.APP_BACKEND_SNAPSHOT_REFRESH_URL ??
    "http://svitlo-power-back-end:5005/internal/v1/snapshots/refresh",
  snapshotStaleThresholdSeconds: Number(
    process.env.APP_BACKEND_REDIS_DASHBOARD_STALE_THRESHOLD_SECONDS ?? 300,
  ),
  snapshotReadsEnabled:
    process.env.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS === "true" &&
    process.env.FEATURE_DASHBOARD_SNAPSHOT_PUBLISH === "true" &&
    process.env.FEATURE_DEYE_POLLING_PROCESSING !== "true",
  apiDocsEnabled:
    process.env.API_DOCS_ENABLED === "true" &&
    process.env.NODE_ENV !== "production",
  logLevel: process.env.APP_LOG_LEVEL ?? "info",
  prettyLogs:
    process.env.APP_LOG_PRETTY === "true" &&
    process.env.NODE_ENV !== "production",
  rateLimitWindowMs: Number(process.env.APP_RATE_LIMIT_WINDOW_MS ?? 60_000),
  rateLimitMax: Number(process.env.APP_RATE_LIMIT_MAX ?? 120),
  rateLimitBlockMs: Number(process.env.APP_RATE_LIMIT_BLOCK_MS ?? 60_000),
}));
