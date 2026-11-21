/**
 * Framework-independent domain types shared by the Node.js services.
 *
 * The shapes mirror the Python Pydantic models in `shared/python` so the
 * Processing service can build byte-compatible `DashboardSnapshot v1` payloads.
 */

export const SUPPORTED_LANGUAGES = ["en", "uk"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

/** Pydantic `LocalizableValue`: a map restricted to the supported locales. */
export type LocalizableValue = Partial<Record<SupportedLanguage, string>>;

export const CHARGE_SOURCES = [
  "None",
  "Grid",
  "Generator",
  "Solar",
  "Recuperation",
] as const;
export type ChargeSource = (typeof CHARGE_SOURCES)[number];

export const SLOT_TYPES = ["Definite", "NotPlanned"] as const;
export type SlotType = (typeof SLOT_TYPES)[number];

export const DAY_STATUSES = [
  "ScheduleApplies",
  "EmergencyShutdowns",
  "WaitingForSchedule",
  "NoOutages",
] as const;
export type DayStatus = (typeof DAY_STATUSES)[number];

export interface OutagesSlot {
  start: number;
  end: number;
  type: SlotType;
}

export interface DaySchedule {
  slots: OutagesSlot[];
  date: string;
  status: DayStatus;
}

export interface UnitSchedule {
  days: DaySchedule[];
  updatedOn: string;
}

export type SchedulesResponse = Record<string, UnitSchedule>;

export interface OutagesScheduleConfig {
  enable: boolean;
  regionId: number | string | null;
  dsoId: number | string | null;
  queue: string | null;
}

export interface ConfigSnapshot {
  title: LocalizableValue;
  outagesSchedule?: OutagesScheduleConfig | null;
}

export interface BuildingSnapshot {
  id: string;
  name: LocalizableValue;
  color: string;
  order: number;
  hasBoundStation: boolean;
  isGridAvailable?: boolean | null;
  gridAvailabilityPct?: number | null;
  hasMixedReporterStates?: boolean | null;
  isCharging?: boolean | null;
  isDischarging?: boolean | null;
  isOffline?: boolean | null;
  batteryPercent?: number | null;
  consumptionPower?: string | null;
  batteryDischargeTime?: string | null;
  batteryChargeTime?: string | null;
  chargeSource: ChargeSource;
  chargePower?: number | null;
}

export interface DashboardSnapshot {
  epoch: number;
  version: number;
  generatedAt: string;
  buildings: BuildingSnapshot[];
  config: ConfigSnapshot;
  outagesSchedules: Record<string, UnitSchedule>;
}

/** Fields that describe a building itself rather than its live measurements. */
export const BUILDING_STATIC_FIELDS = [
  "id",
  "name",
  "color",
  "order",
  "hasBoundStation",
] as const;

export const SNAPSHOT_SECTIONS = [
  "buildings",
  "summary",
  "config",
  "outages",
] as const;
export type SnapshotSection = (typeof SNAPSHOT_SECTIONS)[number];

export const DEFAULT_DASHBOARD_TITLE: LocalizableValue = {
  en: "Dashboard",
  uk: "Панель керування",
};

export const DASHBOARD_SETTING_KEYS = {
  title: "dashboard_title",
  outagesScheduleEnabled: "dashboard_outages_schedule_enabled",
  outagesScheduleRegion: "dashboard_outages_schedule_region",
  outagesScheduleDso: "dashboard_outages_schedule_dso",
  outagesScheduleQueue: "dashboard_outages_schedule_queue",
} as const;

export const LEGACY_YASNO_REGION_NAME = "Kyiv";
export const LEGACY_YASNO_PROVIDER_NAME = "Yasno";
