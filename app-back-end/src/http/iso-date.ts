/**
 * ISO-8601 date-time parsing for the public API.
 *
 * The implementation lives in `@svitlo-power/shared-typescript` so the
 * processing service validates timestamps identically. This module re-exports
 * it to keep the existing `src/http/iso-date.js` import path stable.
 */
export {
  ISO_DATE_TIME_PATTERN,
  isStrictIsoDateTime,
  parseIsoDateTime,
} from "@svitlo-power/shared-typescript";
