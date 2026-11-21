/**
 * Shared health-report vocabulary.
 *
 * Both NestJS services report dependency checks with the same two-state
 * vocabulary, so the type lives here rather than being re-declared per
 * package.
 */
export type CheckStatus = "healthy" | "unhealthy";

export type HealthStatus = "healthy" | "unhealthy";

export type ReadinessStatus = "ready" | "not_ready";

export interface DependencyCheck {
  status: CheckStatus;
  component: string;
  details?: Record<string, unknown>;
}

export interface HealthReport {
  status: HealthStatus;
  checks: Record<string, DependencyCheck>;
  timestamp: string;
}

export interface ReadinessReport {
  status: ReadinessStatus;
  checks: Record<string, CheckStatus>;
}

/** Maps a boolean dependency probe onto the shared check vocabulary. */
export function toCheckStatus(ok: boolean): CheckStatus {
  return ok ? "healthy" : "unhealthy";
}

/** A report is unhealthy when any individual check is unhealthy. */
export function aggregateHealthStatus(
  checks: Record<string, DependencyCheck>,
): HealthStatus {
  return Object.values(checks).some((check) => check.status === "unhealthy")
    ? "unhealthy"
    : "healthy";
}

/** A service is ready only when every dependency check is healthy. */
export function aggregateReadinessStatus(
  checks: Record<string, CheckStatus>,
): ReadinessStatus {
  return Object.values(checks).every((status) => status === "healthy")
    ? "ready"
    : "not_ready";
}
