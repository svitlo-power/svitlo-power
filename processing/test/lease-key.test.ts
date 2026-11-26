import assert from "node:assert/strict";
import { test } from "node:test";
import { leaseKeyFor } from "../src/lease/lease.module.js";
import { LEASE_KEY, SHADOW_LEASE_KEY } from "../src/shared.js";

test("shadow mode leases the shadow key", () => {
  assert.equal(leaseKeyFor(false), SHADOW_LEASE_KEY);
});

test("the cutover leases the production key the write script fences on", () => {
  // Holding the shadow lease while writing production keys would make every
  // publish fail with `lease-lost` even though `lease_held` reports 1.
  assert.equal(leaseKeyFor(true), LEASE_KEY);
  assert.notEqual(LEASE_KEY, SHADOW_LEASE_KEY);
});
