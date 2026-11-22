import assert from "node:assert/strict";
import { test } from "node:test";
import { DBRef } from "bson";
import { Types } from "mongoose";
import { resolveLinkId } from "../src/database/repositories/dashboard.repository.js";

test("link resolution accepts bare ObjectIds and DBRef-like documents", () => {
  const id = new Types.ObjectId();
  assert.equal(resolveLinkId(id), id.toHexString());
  assert.equal(resolveLinkId(id.toHexString()), id.toHexString());
  assert.equal(resolveLinkId({ $ref: "stations", $id: id }), id.toHexString());
  assert.equal(resolveLinkId({ $id: id.toHexString() }), id.toHexString());
  assert.equal(resolveLinkId({ _id: id }), id.toHexString());
  assert.equal(resolveLinkId({ id: id.toHexString() }), id.toHexString());
});

test("link resolution handles the live BSON DBRef shape", () => {
  // The Node driver exposes a DBRef as { collection, oid, db, fields } — the
  // `$id` spelling only exists after a JSON round trip.
  const id = new Types.ObjectId();
  const ref = new DBRef("stations", id);
  assert.equal(resolveLinkId(ref), id.toHexString());
  assert.equal(resolveLinkId({ oid: id }), id.toHexString());
  assert.equal(resolveLinkId({ oid: id.toHexString() }), id.toHexString());
});

test("link resolution rejects values that are not references", () => {
  assert.equal(resolveLinkId(null), null);
  assert.equal(resolveLinkId(undefined), null);
  assert.equal(resolveLinkId("not-an-object-id"), null);
  assert.equal(resolveLinkId({}), null);
  assert.equal(resolveLinkId(42), null);
});
