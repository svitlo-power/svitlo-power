/**
 * MongoDB ObjectId validation.
 *
 * The published snapshot contract (`docs/architecture/snapshot-schema.json`)
 * constrains building ids to `^[0-9a-f]{24}$`, and both services must agree on
 * that rule, so it lives here rather than being re-declared per package.
 *
 * Mongoose is deliberately not used for this check: `Types.ObjectId.isValid()`
 * also accepts 12-byte strings and numbers, which is looser than the contract.
 * Call sites that need a real `ObjectId` instance should construct one with
 * `Types.ObjectId.createFromHexString()` (strict, throws on bad input) after
 * validating with `isObjectId`.
 */
export const OBJECT_ID_PATTERN = /^[0-9a-fA-F]{24}$/;

export function isObjectId(value: unknown): value is string {
  return typeof value === "string" && OBJECT_ID_PATTERN.test(value);
}
