import assert from "node:assert/strict";
import { test } from "node:test";
import { validateEnvironment } from "../src/config/processing.config.js";

test("the environment validation applies the documented defaults", () => {
  const validated = validateEnvironment({});
  assert.equal(validated.PORT, "8100");
  assert.equal(validated.METRICS_PORT, "9099");
  assert.equal(validated.PROCESSING_RECONCILIATION_INTERVAL_SECONDS, "300");
  assert.equal(validated.PROCESSING_REFRESH_COALESCE_MS, "500");
  assert.equal(validated.PROCESSING_LEASE_TTL_SECONDS, "30");
  assert.equal(validated.PROCESSING_LEASE_RENEW_INTERVAL_SECONDS, "10");
  assert.equal(validated.DEYE_REPORT_INTERVAL, "300");
  assert.equal(validated.DEYE_ASSUMED_OFFLINE_REPORTS, "2");
  assert.equal(validated.PROCESSING_LOG_LEVEL, "info");
});

test("the environment validation rejects invalid values", () => {
  assert.throws(
    () => validateEnvironment({ PORT: "0" }),
    /PORT must be an integer >= 1/,
  );
  assert.throws(
    () => validateEnvironment({ PORT: "abc" }),
    /PORT must be an integer >= 1/,
  );
  assert.throws(
    () => validateEnvironment({ PROCESSING_LOG_LEVEL: "verbose" }),
    /PROCESSING_LOG_LEVEL must be a valid Pino level/,
  );
});

test("the environment validation keeps valid overrides", () => {
  const validated = validateEnvironment({
    PORT: "9000",
    METRICS_PORT: "9100",
    PROCESSING_LOG_LEVEL: "debug",
    FEATURE_PROCESSING_SHADOW_MODE: "true",
  });
  assert.equal(validated.PORT, "9000");
  assert.equal(validated.METRICS_PORT, "9100");
  assert.equal(validated.PROCESSING_LOG_LEVEL, "debug");
  assert.equal(validated.FEATURE_PROCESSING_SHADOW_MODE, "true");
});
