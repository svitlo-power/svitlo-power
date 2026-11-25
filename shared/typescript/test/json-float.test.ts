import assert from "node:assert/strict";
import { test } from "node:test";
import {
  SNAPSHOT_FLOAT_FIELDS,
  formatJsonFloat,
  stringifySnapshot,
} from "../src/index.js";

test("formatJsonFloat always keeps a decimal point", () => {
  assert.equal(formatJsonFloat(94), "94.0");
  assert.equal(formatJsonFloat(0), "0.0");
  assert.equal(formatJsonFloat(-3), "-3.0");
  assert.equal(formatJsonFloat(94.5), "94.5");
  assert.equal(formatJsonFloat(1e21), "1e+21");
});

test("stringifySnapshot renders float fields the way Python does", () => {
  const snapshot = {
    buildings: [
      { id: "a", batteryPercent: 94, chargePower: null },
      { id: "b", batteryPercent: 94.5, chargePower: 1 },
    ],
  };

  const json = stringifySnapshot(snapshot);

  assert.match(json, /"batteryPercent":94\.0/);
  assert.match(json, /"batteryPercent":94\.5/);
  assert.match(json, /"chargePower":null/);
  assert.match(json, /"chargePower":1\.0/);
});

test("stringifySnapshot leaves non-float fields untouched", () => {
  const snapshot = {
    order: 1,
    gridAvailabilityPct: 100,
    epoch: 1795358067750,
    hasBoundStation: true,
    name: { en: "Home" },
  };

  const json = stringifySnapshot(snapshot);

  assert.equal(
    json,
    '{"order":1,"gridAvailabilityPct":100,"epoch":1795358067750,"hasBoundStation":true,"name":{"en":"Home"}}',
  );
});

test("stringifySnapshot round-trips to the same values", () => {
  const snapshot = {
    buildings: [{ batteryPercent: 94, chargePower: 2.5 }],
  };

  const parsed = JSON.parse(stringifySnapshot(snapshot));

  assert.equal(parsed.buildings[0].batteryPercent, 94);
  assert.equal(parsed.buildings[0].chargePower, 2.5);
});

test("the float field list matches the legacy Pydantic model", () => {
  assert.deepEqual(
    [...SNAPSHOT_FLOAT_FIELDS],
    ["batteryPercent", "chargePower"],
  );
});
