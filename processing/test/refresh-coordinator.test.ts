import assert from "node:assert/strict";
import { test } from "node:test";
import { RefreshCoordinator } from "../src/triggers/refresh-coordinator.service.js";
import type { ProcessingService } from "../src/processing/processing.service.js";

const TICK_MS = 5;

function coordinator(processing: {
  reconcile: (reason: string) => Promise<unknown>;
}): RefreshCoordinator {
  return new RefreshCoordinator(
    { refreshCoalesceMs: TICK_MS } as never,
    processing as unknown as ProcessingService,
  );
}

test("a failing build rejects every coalesced caller instead of hanging", async () => {
  const instance = coordinator({
    reconcile: async () => {
      throw new Error("mongo down");
    },
  });

  const leader = instance.request("manual");
  const follower = instance.request("manual");

  await assert.rejects(leader, /mongo down/);
  await assert.rejects(follower, /mongo down/);
});

test("a successful build resolves every coalesced caller", async () => {
  const instance = coordinator({
    reconcile: async () => ({
      built: true,
      published: true,
      epoch: 1,
      version: 2,
      changed: [],
      parity: 1,
      mismatches: 0,
      coalesced: false,
    }),
  });

  const [leader, follower] = await Promise.all([
    instance.request("manual"),
    instance.request("manual"),
  ]);

  assert.equal(leader.version, 2);
  assert.equal(follower.version, 2);
  // The follower reports that its request was folded into the leader's build.
  assert.equal(leader.coalesced, false);
  assert.equal(follower.coalesced, true);
});

test("the coordinator accepts a new build after a failure", async () => {
  let attempts = 0;
  const instance = coordinator({
    reconcile: async () => {
      attempts += 1;
      if (attempts === 1) throw new Error("boom");
      return {
        built: true,
        published: true,
        epoch: 1,
        version: 1,
        changed: [],
        parity: 1,
        mismatches: 0,
        coalesced: false,
      };
    },
  });

  await assert.rejects(instance.request("manual"), /boom/);
  const result = await instance.request("manual");
  assert.equal(result.built, true);
  assert.equal(attempts, 2);
});
