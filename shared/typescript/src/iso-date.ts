/**
 * ISO 8601 date/time parsing.
 *
 * The legacy service validated request dates with Python's
 * `datetime.fromisoformat`, which accepts a space separator, a `+HHMM` offset
 * without a colon, and a date-only value. `parseIsoDateTime` reproduces those
 * rules so the NestJS services keep accepting the same payloads.
 */

/**
 * Lenient pattern matching the forms `datetime.fromisoformat` accepts:
 * `YYYY-MM-DD`, an optional `T`/space separator, optional `HH:MM[:SS[.fff]]`,
 * and an optional `Z` or `±HH[:]MM` offset.
 */
export const ISO_DATE_TIME_PATTERN =
  /^(\d{4})-(\d{2})-(\d{2})(?:[T ](\d{2}):(\d{2})(?::(\d{2})(?:[.,](\d{1,6}))?)?(Z|[+-]\d{2}(?::?\d{2})?)?)?$/i;

/**
 * Strict pattern for timestamps the services emit themselves, such as a
 * snapshot's `generatedAt`: a full date-time with seconds and an explicit
 * offset, which is what `Date.prototype.toISOString()` produces.
 */
export const STRICT_ISO_DATE_TIME_PATTERN =
  /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/;

/**
 * Parses the ISO 8601 forms accepted by Python's `datetime.fromisoformat`
 * (the legacy validator) and returns epoch milliseconds, or null when the
 * value is not a valid date. Values without an offset are treated as UTC,
 * matching the legacy service.
 */
export function parseIsoDateTime(value: unknown): number | null {
  if (typeof value !== "string") return null;
  const match = ISO_DATE_TIME_PATTERN.exec(value);
  if (!match) return null;
  const [, year, month, day, hour = "00", minute = "00", second = "00"] = match;
  const fraction = match[7] ?? "";
  const offset = match[8];

  const y = Number(year);
  const mo = Number(month);
  const d = Number(day);
  const calendarDay = new Date(Date.UTC(y, mo - 1, d));
  if (
    calendarDay.getUTCFullYear() !== y ||
    calendarDay.getUTCMonth() !== mo - 1 ||
    calendarDay.getUTCDate() !== d ||
    Number(hour) > 23 ||
    Number(minute) > 59 ||
    Number(second) > 59
  ) {
    return null;
  }

  let offsetMinutes = 0;
  if (offset && offset.toUpperCase() !== "Z") {
    const sign = offset.startsWith("-") ? -1 : 1;
    const digits = offset.slice(1).replace(":", "");
    const hours = Number(digits.slice(0, 2));
    const minutes = Number(digits.slice(2) || "0");
    if (hours > 23 || minutes > 59) return null;
    offsetMinutes = sign * (hours * 60 + minutes);
  }

  const milliseconds = Number(fraction.padEnd(3, "0").slice(0, 3));
  return (
    Date.UTC(y, mo - 1, d, Number(hour), Number(minute), Number(second)) +
    milliseconds -
    offsetMinutes * 60_000
  );
}

/** True when `value` is a full ISO 8601 date-time with an explicit offset. */
export function isStrictIsoDateTime(value: unknown): boolean {
  return typeof value === "string" && STRICT_ISO_DATE_TIME_PATTERN.test(value);
}
