import assert from "node:assert/strict";
import { test } from "node:test";
import { ExecutionContext, UnauthorizedException } from "@nestjs/common";
import { InternalTokenGuard } from "../src/http/internal-token.guard.js";

const TOKEN = "shared-internal-token";

function contextFor(path: string, authorization?: string): ExecutionContext {
  const request = {
    path,
    header: (name: string) =>
      name === "Authorization" ? authorization : undefined,
  };
  return {
    switchToHttp: () => ({ getRequest: () => request }),
  } as unknown as ExecutionContext;
}

function guard(token = TOKEN): InternalTokenGuard {
  return new InternalTokenGuard({
    internalApiToken: token,
  } as never);
}

test("liveness and readiness stay public", () => {
  const instance = guard();
  assert.equal(instance.canActivate(contextFor("/health/live")), true);
  assert.equal(instance.canActivate(contextFor("/health/ready")), true);
});

test("a valid bearer token is accepted", () => {
  const instance = guard();
  assert.equal(
    instance.canActivate(
      contextFor("/internal/v1/snapshots/refresh", `Bearer ${TOKEN}`),
    ),
    true,
  );
});

test("a missing or malformed Authorization header is rejected", () => {
  const instance = guard();
  for (const header of [undefined, "", "Bearer", "Bearer ", "Basic abc"]) {
    assert.throws(
      () =>
        instance.canActivate(
          contextFor("/internal/v1/snapshots/refresh", header),
        ),
      UnauthorizedException,
      String(header),
    );
  }
});

test("a wrong token is rejected", () => {
  const instance = guard();
  assert.throws(
    () =>
      instance.canActivate(
        contextFor("/internal/v1/snapshots/refresh", "Bearer nope"),
      ),
    UnauthorizedException,
  );
});

test("an unconfigured token refuses rather than allowing access", () => {
  const instance = guard("");
  assert.throws(
    () =>
      instance.canActivate(
        contextFor("/internal/v1/snapshots/refresh", "Bearer anything"),
      ),
    /not configured/,
  );
});
