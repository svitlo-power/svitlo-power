import assert from "node:assert/strict";
import { test } from "node:test";
import {
  INVALIDATION_CHANNEL,
  SNAPSHOT_REFRESH_CHANNEL,
  SNAPSHOT_REFRESH_REASONS,
  parseSnapshotRefreshNotification,
} from "../src/index.js";

test("the refresh channel is versioned and separate from the invalidation channel", () => {
  assert.equal(
    SNAPSHOT_REFRESH_CHANNEL,
    "processing:triggers:snapshot-refresh",
  );
  // Overloading the BFF-facing read path would make a rebuild trigger look
  // like a snapshot publication to every consumer.
  assert.notEqual(SNAPSHOT_REFRESH_CHANNEL, INVALIDATION_CHANNEL);
});

test("the documented reasons are all accepted by the trigger endpoint", () => {
  assert.deepEqual(
    [...SNAPSHOT_REFRESH_REASONS],
    ["config-change", "buildings-change", "station-change", "outages-change"],
  );
});

test("a well-formed hint is parsed", () => {
  assert.deepEqual(
    parseSnapshotRefreshNotification(
      JSON.stringify({
        reason: "buildings-change",
        changedSections: ["buildings"],
        source: "back-end",
      }),
    ),
    {
      reason: "buildings-change",
      changedSections: ["buildings"],
      source: "back-end",
    },
  );
});

test("changedSections is optional", () => {
  assert.deepEqual(
    parseSnapshotRefreshNotification(
      JSON.stringify({ reason: "station-change", source: "back-end" }),
    ),
    {
      reason: "station-change",
      source: "back-end",
      changedSections: undefined,
    },
  );
});

test("a payload without a reason or source is dropped", () => {
  // The payload is a hint, never state: anything unusable must be discarded
  // rather than guessed at.
  for (const raw of [
    "not json",
    "null",
    "[]",
    JSON.stringify({ source: "back-end" }),
    JSON.stringify({ reason: "manual" }),
    JSON.stringify({ reason: "", source: "back-end" }),
    JSON.stringify({ reason: "manual", source: "" }),
  ]) {
    assert.equal(parseSnapshotRefreshNotification(raw), null, raw);
  }
});

test("non-string changedSections entries are discarded", () => {
  assert.deepEqual(
    parseSnapshotRefreshNotification(
      JSON.stringify({
        reason: "config-change",
        changedSections: ["config", 7, null],
        source: "back-end",
      }),
    ),
    {
      reason: "config-change",
      changedSections: ["config"],
      source: "back-end",
    },
  );
});
