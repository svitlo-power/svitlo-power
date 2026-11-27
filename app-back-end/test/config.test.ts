import assert from "node:assert/strict";
import { test } from "node:test";
import { appConfig } from "../src/config/app.config.js";

/**
 * The BFF must keep reading the dashboard from Redis after the Phase 5 cutover,
 * when the legacy publisher flag is off but Processing publishes. Gating reads
 * on the legacy flag alone would send every client back to the per-request
 * Mongo path.
 */
function withEnv(
  env: Record<string, string | undefined>,
  fn: () => void,
): void {
  const previous: Record<string, string | undefined> = {};
  for (const [key, value] of Object.entries(env)) {
    previous[key] = process.env[key];
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
  try {
    fn();
  } finally {
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

test("reads require the reader flag", () => {
  withEnv(
    {
      FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS: "false",
      FEATURE_DASHBOARD_SNAPSHOT_PUBLISH: "true",
      FEATURE_PROCESSING_PUBLISH_ENABLED: "false",
      FEATURE_DEYE_POLLING_PROCESSING: "false",
    },
    () => assert.equal(appConfig().snapshotReadsEnabled, false),
  );
});

test("reads stay on after the cutover when Processing publishes", () => {
  withEnv(
    {
      FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS: "true",
      FEATURE_DASHBOARD_SNAPSHOT_PUBLISH: "false",
      FEATURE_PROCESSING_PUBLISH_ENABLED: "true",
      FEATURE_DEYE_POLLING_PROCESSING: "false",
    },
    () => assert.equal(appConfig().snapshotReadsEnabled, true),
  );
});

test("reads stay on while the legacy producer publishes", () => {
  withEnv(
    {
      FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS: "true",
      FEATURE_DASHBOARD_SNAPSHOT_PUBLISH: "true",
      FEATURE_PROCESSING_PUBLISH_ENABLED: "false",
      FEATURE_DEYE_POLLING_PROCESSING: "false",
    },
    () => assert.equal(appConfig().snapshotReadsEnabled, true),
  );
});

test("reads are off when no producer publishes", () => {
  withEnv(
    {
      FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS: "true",
      FEATURE_DASHBOARD_SNAPSHOT_PUBLISH: "false",
      FEATURE_PROCESSING_PUBLISH_ENABLED: "false",
      FEATURE_DEYE_POLLING_PROCESSING: "false",
    },
    () => assert.equal(appConfig().snapshotReadsEnabled, false),
  );
});

test("reads are off while deye polling runs in Processing", () => {
  withEnv(
    {
      FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS: "true",
      FEATURE_DASHBOARD_SNAPSHOT_PUBLISH: "false",
      FEATURE_PROCESSING_PUBLISH_ENABLED: "true",
      FEATURE_DEYE_POLLING_PROCESSING: "true",
    },
    () => assert.equal(appConfig().snapshotReadsEnabled, false),
  );
});
