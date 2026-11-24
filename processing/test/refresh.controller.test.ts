import assert from "node:assert/strict";
import { test } from "node:test";
import { ValidationPipe } from "@nestjs/common";
import { RefreshSnapshotRequestDto } from "../src/triggers/refresh.controller.js";

function pipe(): ValidationPipe {
  return new ValidationPipe({ whitelist: true, forbidNonWhitelisted: true });
}

test("an unknown refresh reason is rejected", async () => {
  const instance = pipe();
  await assert.rejects(
    instance.transform({ reason: "totally-made-up" }, {
      type: "body",
      metatype: RefreshSnapshotRequestDto,
    } as never),
    (error: unknown) => {
      const e = error as { status?: number; response?: { message?: string[] } };
      assert.equal(e.status, 400);
      return true;
    },
  );
});

test("an unknown field is rejected", async () => {
  const instance = pipe();
  await assert.rejects(
    instance.transform({ reason: "manual", injected: true }, {
      type: "body",
      metatype: RefreshSnapshotRequestDto,
    } as never),
    (error: unknown) => (error as { status?: number }).status === 400,
  );
});

test("a known reason passes through", async () => {
  const instance = pipe();
  const result = (await instance.transform(
    { reason: "config-change", requestedBy: "back-end" },
    { type: "body", metatype: RefreshSnapshotRequestDto } as never,
  )) as RefreshSnapshotRequestDto;

  assert.equal(result.reason, "config-change");
  assert.equal(result.requestedBy, "back-end");
});
