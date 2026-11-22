/**
 * JSON serialization that matches Python's `json.dumps` float formatting.
 *
 * Python floats always serialize with a decimal point (`94` -> `94.0`), while
 * JavaScript's `JSON.stringify` emits the shortest round-trippable form
 * (`94.0` -> `94`). The published snapshot contract is defined by the legacy
 * Python producer, so fields the Pydantic model types as `float` must keep the
 * fractional part on the wire.
 *
 * This is a serialization concern only: the numeric value is unchanged, so
 * comparisons and arithmetic behave identically.
 */

/** Fields the legacy `BuildingSnapshot` model declares as `float`. */
export const SNAPSHOT_FLOAT_FIELDS = ["batteryPercent", "chargePower"] as const;

/**
 * Renders a number the way Python renders a float: always with a decimal
 * point, and without exponent notation for the magnitudes a snapshot holds.
 */
export function formatJsonFloat(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  const shortest = String(value);
  if (
    shortest.includes(".") ||
    shortest.includes("e") ||
    shortest.includes("E")
  ) {
    return shortest;
  }
  return `${shortest}.0`;
}

/**
 * Serializes a snapshot, forcing `floatFields` to render with a decimal point.
 *
 * `JSON.stringify` has no hook for number formatting, so each float field is
 * replaced with a unique string token before stringifying and swapped back
 * afterwards. The token is quoted in the JSON output, so the replacement
 * targets the quoted form.
 */
export function stringifySnapshot(
  snapshot: unknown,
  floatFields: readonly string[] = SNAPSHOT_FLOAT_FIELDS,
): string {
  const tokens = new Map<string, number>();

  const encode = (value: unknown): unknown => {
    if (Array.isArray(value)) return value.map(encode);
    if (value !== null && typeof value === "object") {
      const result: Record<string, unknown> = {};
      for (const [key, entry] of Object.entries(value)) {
        if (floatFields.includes(key) && typeof entry === "number") {
          const token = `\u0000svitlo-float-${tokens.size}\u0000`;
          tokens.set(token, entry);
          result[key] = token;
          continue;
        }
        result[key] = encode(entry);
      }
      return result;
    }
    return value;
  };

  let json = JSON.stringify(encode(snapshot));
  for (const [token, value] of tokens) {
    json = json.replace(JSON.stringify(token), formatJsonFloat(value));
  }
  return json;
}
