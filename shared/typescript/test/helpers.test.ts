import assert from "node:assert/strict";
import { test } from "node:test";
import {
  aggregateHealthStatus,
  aggregateReadinessStatus,
  isObjectId,
  isStrictIsoDateTime,
  OBJECT_ID_PATTERN,
  parseIsoDateTime,
  toCheckStatus,
} from "../src/index.js";

test("ObjectId validation accepts only 24-char hex", () => {
  assert.equal(isObjectId("507f1f77bcf86cd799439011"), true);
  assert.equal(isObjectId("507F1F77BCF86CD799439011"), true);
  assert.equal(OBJECT_ID_PATTERN.test("507f1f77bcf86cd799439011"), true);

  for (const invalid of [
    undefined,
    null,
    42,
    "",
    "507f1f77bcf86cd79943901",
    "507f1f77bcf86cd7994390111",
    "abcdefghijkl",
    "507f1f77bcf86cd79943901z",
  ]) {
    assert.equal(isObjectId(invalid), false, String(invalid));
  }
});

test("parseIsoDateTime accepts the legacy fromisoformat forms", () => {
  assert.equal(parseIsoDateTime("2026-01-01T00:00:00Z"), Date.UTC(2026, 0, 1));
  assert.equal(parseIsoDateTime("2026-01-01"), Date.UTC(2026, 0, 1));
  assert.equal(
    parseIsoDateTime("2026-01-01 02:00:00.5+0200"),
    Date.UTC(2026, 0, 1, 0, 0, 0, 500),
  );
  assert.equal(parseIsoDateTime("2026-01-01T00:00"), Date.UTC(2026, 0, 1));
  assert.equal(
    parseIsoDateTime("2026-01-01T00:00:00+02:00"),
    Date.UTC(2025, 11, 31, 22),
  );
});

test("parseIsoDateTime rejects malformed and overflowed values", () => {
  for (const invalid of [
    undefined,
    null,
    1767225600000,
    "",
    "Jan 1 2026",
    "2026",
    "2026-13-01",
    "2026-02-29",
    "2026-02-30T00:00:00Z",
    "2026-01-01T24:00:00",
    "2026-01-01T00:60:00",
    "2026-01-01T00:00:00+25:00",
  ]) {
    assert.equal(parseIsoDateTime(invalid), null, String(invalid));
  }
});

test("isStrictIsoDateTime requires seconds and an explicit offset", () => {
  assert.equal(isStrictIsoDateTime(new Date().toISOString()), true);
  assert.equal(isStrictIsoDateTime("2026-01-01T00:00:00.123+02:00"), true);

  for (const invalid of [
    undefined,
    "2026-01-01",
    "2026-01-01T00:00",
    "2026-01-01T00:00:00",
    "2026-01-01 00:00:00Z",
    "2026-01-01T00:00:00+0200",
  ]) {
    assert.equal(isStrictIsoDateTime(invalid), false, String(invalid));
  }
});

test("health helpers map probes onto the shared vocabulary", () => {
  assert.equal(toCheckStatus(true), "healthy");
  assert.equal(toCheckStatus(false), "unhealthy");

  assert.equal(
    aggregateHealthStatus({
      redis: { status: "healthy", component: "redis" },
      api: { status: "unhealthy", component: "api" },
    }),
    "unhealthy",
  );
  assert.equal(
    aggregateHealthStatus({
      redis: { status: "healthy", component: "redis" },
    }),
    "healthy",
  );

  assert.equal(
    aggregateReadinessStatus({ redis: "healthy", snapshot: "healthy" }),
    "ready",
  );
  assert.equal(
    aggregateReadinessStatus({ redis: "healthy", snapshot: "unhealthy" }),
    "not_ready",
  );
});
