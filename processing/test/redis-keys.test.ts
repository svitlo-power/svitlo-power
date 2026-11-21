import assert from "node:assert/strict";
import { test } from "node:test";
import {
  LUA_LEASE_RENEW_SCRIPT,
  LUA_LEASE_RELEASE_SCRIPT,
  LUA_SHADOW_WRITE_SCRIPT,
  SHADOW_EPOCH_KEY,
  SHADOW_INVALIDATION_CHANNEL,
  SHADOW_KEYS,
  SHADOW_LEASE_KEY,
  SHADOW_SNAPSHOT_KEY,
  SHADOW_VERSION_COMMITTED_KEY,
  SHADOW_VERSION_NEXT_KEY,
  SNAPSHOT_KEY,
  isShadowKey,
  parseShadowWriteResult,
} from "../src/shared.js";

test("every shadow key is isolated from the production namespace", () => {
  for (const key of SHADOW_KEYS) {
    assert.ok(isShadowKey(key), `${key} must be shadow-prefixed`);
    assert.notEqual(key, SNAPSHOT_KEY);
  }
  assert.equal(SHADOW_SNAPSHOT_KEY, "shadow:cache:dashboard:v1:global");
  assert.equal(
    SHADOW_INVALIDATION_CHANNEL,
    "shadow:cache:dashboard:v1:invalidations",
  );
  assert.equal(SHADOW_LEASE_KEY, "shadow:lock:processing:dashboard:v1");
  assert.equal(SHADOW_EPOCH_KEY, "shadow:meta:dashboard:epoch");
  assert.equal(SHADOW_VERSION_NEXT_KEY, "shadow:meta:dashboard:version:next");
  assert.equal(SHADOW_VERSION_COMMITTED_KEY, "shadow:meta:dashboard:version");
});

test("the shadow write script fences on the lease and CASes on the version", () => {
  // The script must never reference a production key literal.
  assert.ok(LUA_SHADOW_WRITE_SCRIPT.includes("redis.call('GET', KEYS[3])"));
  assert.ok(LUA_SHADOW_WRITE_SCRIPT.includes("'lease-lost'"));
  assert.ok(LUA_SHADOW_WRITE_SCRIPT.includes("'epoch-stale'"));
  assert.ok(LUA_SHADOW_WRITE_SCRIPT.includes("'version-stale'"));
  assert.ok(!LUA_SHADOW_WRITE_SCRIPT.includes("cache:dashboard:v1:global"));
  assert.ok(!LUA_SHADOW_WRITE_SCRIPT.includes("meta:dashboard:epoch"));
});

test("lease scripts only act for the current holder", () => {
  assert.ok(LUA_LEASE_RENEW_SCRIPT.includes("EXPIRE"));
  assert.ok(LUA_LEASE_RELEASE_SCRIPT.includes("DEL"));
  assert.ok(LUA_LEASE_RENEW_SCRIPT.includes("== ARGV[1]"));
  assert.ok(LUA_LEASE_RELEASE_SCRIPT.includes("== ARGV[1]"));
});

test("shadow write results are parsed into a stable shape", () => {
  assert.deepEqual(parseShadowWriteResult([1, "ok", "epoch=1,version=2"]), {
    success: true,
    reason: "ok",
    detail: "epoch=1,version=2",
  });
  assert.deepEqual(
    parseShadowWriteResult([0, "lease-lost", "not-lease-holder"]),
    {
      success: false,
      reason: "lease-lost",
      detail: "not-lease-holder",
    },
  );
  assert.deepEqual(parseShadowWriteResult("unexpected"), {
    success: false,
    reason: "malformed-result",
  });
});
