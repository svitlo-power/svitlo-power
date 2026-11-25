/**
 * Deterministic field-level comparison between two `DashboardSnapshot v1`
 * payloads.
 *
 * The comparison ignores `generatedAt` (always different) and reports one
 * mismatch per differing leaf field so the shadow metrics can be aggregated by
 * section and field name.
 */
import {
  BUILDING_STATIC_FIELDS,
  DashboardSnapshot,
  SNAPSHOT_SECTIONS,
  SnapshotSection,
} from "./domain.js";

export interface SnapshotMismatch {
  section: SnapshotSection | "snapshot";
  field: string;
  expected: unknown;
  actual: unknown;
}

export interface SnapshotDiff {
  matches: boolean;
  mismatches: SnapshotMismatch[];
  /** Fraction of compared leaf fields that matched, 1 for an exact match. */
  parity: number;
  comparedFields: number;
  /** Building ids present in one snapshot but not the other. */
  missingBuildings: string[];
  extraBuildings: string[];
}

const STATIC_FIELD_SET = new Set<string>(BUILDING_STATIC_FIELDS);

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Normalises a value so key order and undefined-vs-missing never matter. */
function canonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(canonical);
  if (value instanceof Date) return value.toISOString();
  if (isPlainObject(value)) {
    const result: Record<string, unknown> = {};
    for (const key of Object.keys(value).sort()) {
      const entry = value[key];
      if (entry === undefined) continue;
      result[key] = canonical(entry);
    }
    return result;
  }
  return value;
}

function stable(value: unknown): string {
  return JSON.stringify(canonical(value)) ?? "null";
}

function buildingSummary(building: Record<string, unknown>) {
  const summary: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(building)) {
    if (STATIC_FIELD_SET.has(key)) continue;
    summary[key] = value;
  }
  return summary;
}

function buildingStatic(building: Record<string, unknown>) {
  const statics: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(building)) {
    if (!STATIC_FIELD_SET.has(key)) continue;
    statics[key] = value;
  }
  return statics;
}

/**
 * Returns the subset of `["buildings","summary","config","outages"]` that
 * changed, matching `DashboardSnapshotService._changed_sections`.
 */
export function changedSections(
  previous: DashboardSnapshot | null,
  current: DashboardSnapshot,
): SnapshotSection[] {
  if (previous === null) return [...SNAPSHOT_SECTIONS];

  const changes: SnapshotSection[] = [];
  const previousBuildings = previous.buildings.map((building) =>
    buildingStatic(building as unknown as Record<string, unknown>),
  );
  const currentBuildings = current.buildings.map((building) =>
    buildingStatic(building as unknown as Record<string, unknown>),
  );
  if (stable(previousBuildings) !== stable(currentBuildings)) {
    changes.push("buildings");
  }

  const previousSummaries: Record<string, unknown> = {};
  for (const building of previous.buildings) {
    previousSummaries[building.id] = buildingSummary(
      building as unknown as Record<string, unknown>,
    );
  }
  const currentSummaries: Record<string, unknown> = {};
  for (const building of current.buildings) {
    currentSummaries[building.id] = buildingSummary(
      building as unknown as Record<string, unknown>,
    );
  }
  if (stable(previousSummaries) !== stable(currentSummaries)) {
    changes.push("summary");
  }

  if (stable(previous.config) !== stable(current.config))
    changes.push("config");
  if (stable(previous.outagesSchedules) !== stable(current.outagesSchedules)) {
    changes.push("outages");
  }
  return changes;
}

/**
 * Compares two snapshots field by field. `generatedAt`, `epoch` and `version`
 * are excluded: they legitimately differ between producers.
 */
export function diffSnapshots(
  expected: DashboardSnapshot,
  actual: DashboardSnapshot,
): SnapshotDiff {
  const mismatches: SnapshotMismatch[] = [];
  let comparedFields = 0;

  const compare = (
    section: SnapshotDiff["mismatches"][number]["section"],
    field: string,
    left: unknown,
    right: unknown,
  ): void => {
    comparedFields += 1;
    if (stable(left) !== stable(right)) {
      mismatches.push({ section, field, expected: left, actual: right });
    }
  };

  compare(
    "snapshot",
    "buildings:length",
    expected.buildings.length,
    actual.buildings.length,
  );

  // Buildings are matched by id, not by position: one added, removed or
  // reordered building must not shift every later row into a false mismatch.
  const expectedById = new Map(
    expected.buildings.map((building) => [building.id, building]),
  );
  const actualById = new Map(
    actual.buildings.map((building) => [building.id, building]),
  );
  const missingBuildings = [...expectedById.keys()].filter(
    (id) => !actualById.has(id),
  );
  const extraBuildings = [...actualById.keys()].filter(
    (id) => !expectedById.has(id),
  );
  for (const id of missingBuildings) {
    compare("buildings", `buildings.${id}`, expectedById.get(id) ?? null, null);
  }
  for (const id of extraBuildings) {
    compare("buildings", `buildings.${id}`, null, actualById.get(id) ?? null);
  }

  for (const [id, left] of expectedById) {
    const right = actualById.get(id);
    if (!right) continue;
    for (const key of new Set([...Object.keys(left), ...Object.keys(right)])) {
      const section = STATIC_FIELD_SET.has(key) ? "buildings" : "summary";
      compare(
        section,
        `${id}.${key}`,
        (left as unknown as Record<string, unknown>)[key] ?? null,
        (right as unknown as Record<string, unknown>)[key] ?? null,
      );
    }
  }

  compare("config", "config.title", expected.config.title, actual.config.title);
  compare(
    "config",
    "config.outagesSchedule",
    expected.config.outagesSchedule ?? null,
    actual.config.outagesSchedule ?? null,
  );

  const expectedQueues = Object.keys(expected.outagesSchedules).sort();
  const actualQueues = Object.keys(actual.outagesSchedules).sort();
  compare("outages", "outagesSchedules.queues", expectedQueues, actualQueues);
  for (const queue of new Set([...expectedQueues, ...actualQueues])) {
    compare(
      "outages",
      `outagesSchedules.${queue}`,
      expected.outagesSchedules[queue] ?? null,
      actual.outagesSchedules[queue] ?? null,
    );
  }

  return {
    matches: mismatches.length === 0,
    mismatches,
    parity:
      comparedFields === 0
        ? 1
        : (comparedFields - mismatches.length) / comparedFields,
    comparedFields,
    missingBuildings,
    extraBuildings,
  };
}
