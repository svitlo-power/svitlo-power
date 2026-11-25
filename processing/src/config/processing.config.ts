import { readFileSync } from "node:fs";
import { registerAs } from "@nestjs/config";

function readVersion(): string {
  if (process.env.APP_VERSION) return process.env.APP_VERSION;
  try {
    return readFileSync("/app/VERSION", "utf8").trim() || "0000.00.00";
  } catch {
    return "0000.00.00";
  }
}

export interface ProcessingConfiguration {
  version: string;
  port: number;
  metricsPort: number;
  mongoUri: string;
  mongoDatabase: string;
  redisUrl: string;
  /** Shared bearer token required by the internal refresh trigger. */
  internalApiToken: string;
  logLevel: string;
  prettyLogs: boolean;
  /** Enables the shadow snapshot flow (build + compare + shadow writes). */
  shadowModeEnabled: boolean;
  /** Interval between scheduled shadow reconciliations. */
  reconciliationIntervalMs: number;
  /** Debounce window that coalesces bursts of refresh requests. */
  refreshCoalesceMs: number;
  /**
   * Maximum tolerated age difference between the production and shadow
   * snapshots. Beyond it the comparison is skipped instead of reporting
   * mismatches caused purely by time skew.
   */
  comparisonMaxSkewSeconds: number;
  deyeReportIntervalSeconds: number;
  deyeAssumedOfflineReports: number;
  leaseTtlSeconds: number;
  leaseRenewIntervalSeconds: number;
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
  const logLevel = String(env.PROCESSING_LOG_LEVEL ?? "info");
  if (
    !["trace", "debug", "info", "warn", "error", "fatal", "silent"].includes(
      logLevel,
    )
  ) {
    throw new Error("PROCESSING_LOG_LEVEL must be a valid Pino level");
  }
  const result: Record<string, unknown> = {
    ...env,
    PORT: positiveInteger(env, "PORT", 8100),
    METRICS_PORT: positiveInteger(env, "METRICS_PORT", 9095),
    PROCESSING_RECONCILIATION_INTERVAL_SECONDS: positiveInteger(
      env,
      "PROCESSING_RECONCILIATION_INTERVAL_SECONDS",
      300,
    ),
    PROCESSING_REFRESH_COALESCE_MS: positiveInteger(
      env,
      "PROCESSING_REFRESH_COALESCE_MS",
      500,
    ),
    PROCESSING_COMPARISON_MAX_SKEW_SECONDS: positiveInteger(
      env,
      "PROCESSING_COMPARISON_MAX_SKEW_SECONDS",
      120,
    ),
    DEYE_REPORT_INTERVAL: positiveInteger(env, "DEYE_REPORT_INTERVAL", 300),
    DEYE_ASSUMED_OFFLINE_REPORTS: positiveInteger(
      env,
      "DEYE_ASSUMED_OFFLINE_REPORTS",
      2,
    ),
    PROCESSING_LEASE_TTL_SECONDS: positiveInteger(
      env,
      "PROCESSING_LEASE_TTL_SECONDS",
      30,
    ),
    PROCESSING_LEASE_RENEW_INTERVAL_SECONDS: positiveInteger(
      env,
      "PROCESSING_LEASE_RENEW_INTERVAL_SECONDS",
      10,
    ),
    PROCESSING_LOG_LEVEL: logLevel,
    INTERNAL_API_TOKEN: String(env.INTERNAL_API_TOKEN ?? ""),
  };

  const ttl = Number(result.PROCESSING_LEASE_TTL_SECONDS);
  const renew = Number(result.PROCESSING_LEASE_RENEW_INTERVAL_SECONDS);
  // A renewal interval at or above the TTL means the lease can expire between
  // renewals, so the instance would lose the lease on a normal cycle.
  if (renew >= ttl) {
    throw new Error(
      "PROCESSING_LEASE_RENEW_INTERVAL_SECONDS must be less than PROCESSING_LEASE_TTL_SECONDS",
    );
  }
  return result;
}

export const processingConfig = registerAs(
  "processing",
  (): ProcessingConfiguration => ({
    version: readVersion(),
    port: Number(process.env.PORT ?? 8100),
    metricsPort: Number(process.env.METRICS_PORT ?? 9095),
    mongoUri: process.env.MONGO_URI ?? "mongodb://127.0.0.1:27017",
    mongoDatabase: process.env.MONGO_DB ?? "svitlo-power",
    redisUrl: process.env.REDIS_URI ?? "redis://svitlo-power-rds:6379/0",
    internalApiToken: process.env.INTERNAL_API_TOKEN ?? "",
    logLevel: process.env.PROCESSING_LOG_LEVEL ?? "info",
    prettyLogs:
      process.env.PROCESSING_LOG_PRETTY === "true" &&
      process.env.NODE_ENV !== "production",
    shadowModeEnabled: process.env.FEATURE_PROCESSING_SHADOW_MODE === "true",
    reconciliationIntervalMs:
      Number(process.env.PROCESSING_RECONCILIATION_INTERVAL_SECONDS ?? 300) *
      1000,
    refreshCoalesceMs: Number(
      process.env.PROCESSING_REFRESH_COALESCE_MS ?? 500,
    ),
    comparisonMaxSkewSeconds: Number(
      process.env.PROCESSING_COMPARISON_MAX_SKEW_SECONDS ?? 120,
    ),
    deyeReportIntervalSeconds: Number(process.env.DEYE_REPORT_INTERVAL ?? 300),
    deyeAssumedOfflineReports: Number(
      process.env.DEYE_ASSUMED_OFFLINE_REPORTS ?? 2,
    ),
    leaseTtlSeconds: Number(process.env.PROCESSING_LEASE_TTL_SECONDS ?? 30),
    leaseRenewIntervalSeconds: Number(
      process.env.PROCESSING_LEASE_RENEW_INTERVAL_SECONDS ?? 10,
    ),
  }),
);
