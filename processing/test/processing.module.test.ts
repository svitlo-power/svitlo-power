import assert from "node:assert/strict";
import { test } from "node:test";
import { selectActivePublisher } from "../src/processing/processing.module.js";
import type { ShadowPublisher } from "../src/shadow/shadow-publisher.service.js";
import type { SnapshotPublisher } from "../src/snapshot/snapshot-publisher.service.js";

/**
 * The publisher is chosen from the publish flag, not from whether a provider
 * was injected. The unit tests build `ProcessingService` by hand and pass a
 * publisher directly, so they cannot catch a module that always injects the
 * production publisher (the H1 regression); this drives the selection factory
 * the module uses.
 */

const shadow = {} as ShadowPublisher;
const production = {} as SnapshotPublisher;

test("shadow mode selects the shadow publisher", () => {
  const selected = selectActivePublisher(
    { publishEnabled: false } as never,
    shadow,
    production,
  );
  // Writing to the production keys in shadow mode would raise the production
  // epoch and stall the legacy producer.
  assert.equal(selected, shadow);
});

test("the cutover selects the production publisher", () => {
  const selected = selectActivePublisher(
    { publishEnabled: true } as never,
    shadow,
    production,
  );
  assert.equal(selected, production);
});
