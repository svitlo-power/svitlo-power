import assert from "node:assert/strict";
import { test } from "node:test";
import { MetricsService } from "../src/metrics/metrics.service.js";

function metrics(shadowModeEnabled: boolean): MetricsService {
  return new MetricsService({
    version: "0000.00.00",
    shadowModeEnabled,
    publishEnabled: false,
  } as never);
}

/** Value of a single-sample gauge in the exported text, or `undefined`. */
function sample(body: string, name: string): string | undefined {
  const line = body
    .split("\n")
    .find((candidate) => candidate.startsWith(`${name} `));
  return line?.slice(name.length + 1);
}

test("a fresh instance exports no parity sample and no epoch-0 timestamp", async () => {
  const body = await metrics(true).registry.metrics();

  // An unset gauge is exported as `0`, so both shadow gauges have to be seeded
  // explicitly: `0` parity would read as 0% and an epoch-0 timestamp would make
  // `time() - ts` exceed any freshness threshold.
  assert.equal(sample(body, "processing_shadow_parity_rate"), "Nan");
  const lastComparison = Number(
    sample(body, "processing_shadow_last_comparison_timestamp_seconds"),
  );
  assert.ok(
    Math.abs(Date.now() / 1000 - lastComparison) < 60,
    `expected the process start time, got ${lastComparison}`,
  );
});

test("shadow mode off reports the mode gauge as 0 and leaves the timestamp unset", async () => {
  const body = await metrics(false).registry.metrics();

  assert.equal(sample(body, "processing_shadow_mode_enabled"), "0");
  // Nothing is expected to compare, so the freshness rule must not match this
  // instance at all.
  assert.equal(
    sample(body, "processing_shadow_last_comparison_timestamp_seconds"),
    undefined,
  );
  assert.equal(sample(body, "processing_shadow_lease_held"), "0");
});

test("a completed comparison replaces the seeded parity and timestamp", async () => {
  const service = metrics(true);
  const before = Date.now() / 1000;

  service.setShadowParity(0.9999);
  const body = await service.registry.metrics();

  assert.equal(sample(body, "processing_shadow_parity_rate"), "0.9999");
  const lastComparison = Number(
    sample(body, "processing_shadow_last_comparison_timestamp_seconds"),
  );
  assert.ok(lastComparison >= before);
});

test("a skipped comparison leaves parity without a numeric value", async () => {
  const service = metrics(true);
  service.setShadowParity(0.9999);

  service.markShadowParityStale();
  const body = await service.registry.metrics();

  // `0` must keep meaning "0% parity", so a skip cannot be read as a real
  // sample by a future `parity < X` alert.
  assert.equal(sample(body, "processing_shadow_parity_rate"), "Nan");
});

test("the publish gauge reports whether this instance owns the cutover", async () => {
  const shadowOnly = new MetricsService({
    version: "0000.00.00",
    shadowModeEnabled: true,
    publishEnabled: false,
  } as never);
  assert.equal(
    sample(await shadowOnly.registry.metrics(), "processing_publish_enabled"),
    "0",
  );

  const publishing = new MetricsService({
    version: "0000.00.00",
    shadowModeEnabled: true,
    publishEnabled: true,
  } as never);
  assert.equal(
    sample(await publishing.registry.metrics(), "processing_publish_enabled"),
    "1",
  );
});
