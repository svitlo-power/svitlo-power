/**
 * Port of the schedule-id normalisation and outages-config rules from
 * `shared/python/shared/services/dashboard/service.py` and
 * `shared/python/shared/models/dashboard_config.py`.
 */
import {
  LEGACY_YASNO_PROVIDER_NAME,
  LEGACY_YASNO_REGION_NAME,
  OutagesScheduleConfig,
} from "./domain.js";

/**
 * Mirrors `ReadOnlyDashboardService._normalize_schedule_id`.
 *
 * Booleans are rejected, positive integers pass through, and strings are
 * trimmed and converted to a positive integer when they are decimal.
 */
export function normalizeScheduleId(value: unknown): number | string | null {
  if (typeof value === "boolean") return null;
  if (typeof value === "number") {
    return Number.isFinite(value) && value > 0 ? value : null;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (/^[0-9]+$/.test(trimmed)) {
      const parsed = Number.parseInt(trimmed, 10);
      return parsed > 0 ? parsed : trimmed;
    }
    return trimmed;
  }
  return null;
}

export interface OutagesScheduleSettings {
  title: Record<string, string>;
  enabled: boolean;
  region: unknown;
  dso: unknown;
  queue: string;
}

export interface DashboardConfigResult {
  title: Record<string, string>;
  outagesSchedule: OutagesScheduleConfig;
  enableOutagesSchedule: boolean;
  outagesScheduleQueue: string | null;
}

/**
 * Builds the dashboard config the same way the legacy producer does: the
 * schedule is only enabled when it is fully configured.
 */
export function buildDashboardConfig(
  settings: OutagesScheduleSettings,
): DashboardConfigResult {
  const regionId = normalizeScheduleId(settings.region);
  const dsoId = normalizeScheduleId(settings.dso);
  const queue = settings.queue ?? "";
  const scheduleIsConfigured =
    regionId !== null && dsoId !== null && Boolean(queue.trim());
  const enabled = Boolean(settings.enabled) && scheduleIsConfigured;
  return {
    title: settings.title,
    outagesSchedule: {
      enable: enabled,
      regionId,
      dsoId,
      queue: queue || null,
    },
    enableOutagesSchedule: enabled,
    outagesScheduleQueue: queue || null,
  };
}

/**
 * Accepts the legacy flat `enable_outages_schedule` / `outages_schedule_queue`
 * settings pair and promotes it to the nested schedule shape, matching
 * `DashboardConfig.migrate_legacy_outages_schedule`.
 */
export function migrateLegacyOutagesSchedule(value: unknown): unknown {
  if (typeof value !== "object" || value === null) return value;
  const record = value as Record<string, unknown>;
  const hasLegacySchedule =
    "enable_outages_schedule" in record || "outages_schedule_queue" in record;
  if (record.outages_schedule === null && hasLegacySchedule) {
    const enabled = Boolean(record.enable_outages_schedule ?? false);
    return {
      ...record,
      outages_schedule: enabled
        ? {
            enable: true,
            regionId: LEGACY_YASNO_REGION_NAME,
            dsoId: LEGACY_YASNO_PROVIDER_NAME,
            queue: record.outages_schedule_queue ?? null,
          }
        : { enable: false, region: null, dso: null, queue: null },
    };
  }
  return value;
}

/** Keeps only `Definite` slots, matching `SchedulesResponse.clean_slots`. */
export function keepOnlyDefiniteSlots<T extends { slots: { type: string }[] }>(
  schedule: Record<string, { days: T[] }>,
): Record<string, { days: T[] }> {
  const result: Record<string, { days: T[] }> = {};
  for (const [queue, unit] of Object.entries(schedule)) {
    result[queue] = {
      ...unit,
      days: unit.days.map((day) => ({
        ...day,
        slots: day.slots.filter((slot) => slot.type === "Definite"),
      })),
    };
  }
  return result;
}
