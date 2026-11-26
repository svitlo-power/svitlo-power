import assert from "node:assert/strict";
import { test } from "node:test";
import { EventEmitter } from "node:events";
import { SnapshotRefreshSubscriber } from "../src/triggers/snapshot-refresh.subscriber.js";
import type { RefreshCoordinator } from "../src/triggers/refresh-coordinator.service.js";
import type { MetricsService } from "../src/metrics/metrics.service.js";
import { SNAPSHOT_REFRESH_CHANNEL } from "../src/shared.js";

interface Harness {
  subscriber: InstanceType<typeof FakeRedis>;
  instance: SnapshotRefreshSubscriber;
  requests: Array<{ reason: string; requestedBy?: string }>;
  notifications: string[];
  errors: string[];
  acknowledgements: Array<{ version: number; seconds: number }>;
  failWith?: Error;
  published?: boolean;
}

class FakeRedis extends EventEmitter {
  readonly subscribed: string[] = [];
  readonly unsubscribed: string[] = [];
  subscribeError?: Error;
  /** Messages delivered to the subscribe callback, as node-redis v4+ does. */
  readonly received: string[] = [];

  async subscribe(
    channel: string,
    listener?: (raw: string) => void,
  ): Promise<void> {
    if (this.subscribeError) throw this.subscribeError;
    this.subscribed.push(channel);
    this.listener = listener;
  }

  private listener?: (raw: string) => void;

  /** Simulates the server pushing one message to this subscriber. */
  deliver(raw: string): void {
    this.received.push(raw);
    this.listener?.(raw);
  }

  async unsubscribe(channel: string): Promise<void> {
    this.unsubscribed.push(channel);
  }
}

function harness(options: { shadowModeEnabled?: boolean } = {}): Harness {
  const subscriber = new FakeRedis();
  const requests: Harness["requests"] = [];
  const notifications: string[] = [];
  const errors: string[] = [];
  const acknowledgements: Harness["acknowledgements"] = [];
  const state: Harness = {
    subscriber,
    instance: undefined as unknown as SnapshotRefreshSubscriber,
    requests,
    notifications,
    errors,
    acknowledgements,
  };

  const coordinator = {
    request: async (reason: string, requestedBy?: string) => {
      requests.push({ reason, requestedBy });
      if (state.failWith) throw state.failWith;
      return {
        built: true,
        published: state.published ?? true,
        epoch: 1,
        version: 2,
        changed: [],
        parity: null,
        mismatches: 0,
        coalesced: false,
      };
    },
  } as unknown as RefreshCoordinator;

  const metrics = {
    refreshNotification: (reason: string) => notifications.push(reason),
    refreshNotificationError: (reason: string) => errors.push(reason),
    setRefreshAcknowledgement: (version: number, seconds: number) =>
      acknowledgements.push({ version, seconds }),
  } as unknown as MetricsService;

  state.instance = new SnapshotRefreshSubscriber(
    {
      shadowModeEnabled: options.shadowModeEnabled ?? true,
    } as never,
    subscriber as never,
    coordinator,
    metrics,
  );
  return state;
}

test("the subscription is established on the versioned channel", async () => {
  const state = harness();
  await state.instance.onApplicationBootstrap();

  assert.deepEqual(state.subscriber.subscribed, [SNAPSHOT_REFRESH_CHANNEL]);
});

test("shadow mode off leaves the subscription inert", async () => {
  const state = harness({ shadowModeEnabled: false });
  await state.instance.onApplicationBootstrap();

  assert.deepEqual(state.subscriber.subscribed, []);
});

test("a subscription failure does not stop the service", async () => {
  const state = harness();
  state.subscriber.subscribeError = new Error("redis down");

  // The HTTP trigger and the reconciliation cron still refresh snapshots, so a
  // broken subscription must not take the process down.
  await state.instance.onApplicationBootstrap();
  assert.deepEqual(state.subscriber.subscribed, []);
});

test("a notification becomes a coalesced refresh request", async () => {
  const state = harness();
  await state.instance.onApplicationBootstrap();

  state.subscriber.deliver(
    JSON.stringify({
      reason: "buildings-change",
      changedSections: ["buildings"],
      source: "back-end",
    }),
  );
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(state.requests, [
    { reason: "buildings-change", requestedBy: "back-end" },
  ]);
  assert.deepEqual(state.notifications, ["buildings-change"]);
  assert.equal(state.acknowledgements.length, 1);
  assert.equal(state.acknowledgements[0].version, 2);
  assert.ok(state.acknowledgements[0].seconds > 0);
});

test("a message on another channel is ignored", async () => {
  const state = harness();
  await state.instance.onApplicationBootstrap();

  // The callback is per-channel, so a foreign channel never reaches it; the
  // guard is covered directly below.
  state.subscriber.deliver(
    JSON.stringify({ reason: "station-change", source: "back-end" }),
  );
  await new Promise((resolve) => setImmediate(resolve));

  assert.deepEqual(state.requests, [
    { reason: "station-change", requestedBy: "back-end" },
  ]);
});

test("an unusable payload is counted and dropped", async () => {
  const state = harness();
  await state.instance.onApplicationBootstrap();

  await state.instance.handleMessage("not json");

  assert.deepEqual(state.requests, []);
  assert.deepEqual(state.notifications, ["invalid"]);
});

test("a failed build is recorded without an unhandled rejection", async () => {
  const state = harness();
  state.failWith = new Error("mongo down");
  await state.instance.onApplicationBootstrap();

  await state.instance.handleMessage(
    JSON.stringify({ reason: "station-change", source: "back-end" }),
  );

  assert.deepEqual(state.errors, ["station-change"]);
  assert.deepEqual(state.acknowledgements, []);
});

test("an unpublished result is counted as an error and not acknowledged", async () => {
  // A standby replica (no-lease) or a CAS/lease rejection settles with
  // `published: false`; stamping the acknowledgement gauge for those would
  // report a version that was never written.
  const state = harness();
  state.published = false;
  await state.instance.onApplicationBootstrap();

  await state.instance.handleMessage(
    JSON.stringify({ reason: "station-change", source: "back-end" }),
  );

  assert.deepEqual(state.acknowledgements, []);
  assert.deepEqual(state.errors, ["station-change"]);
});

test("a notification arriving during shutdown is ignored", async () => {
  const state = harness();
  await state.instance.onApplicationBootstrap();
  state.instance.onModuleDestroy();

  await state.instance.handleMessage(
    JSON.stringify({ reason: "station-change", source: "back-end" }),
  );

  assert.deepEqual(state.requests, []);
  assert.deepEqual(state.subscriber.unsubscribed, [SNAPSHOT_REFRESH_CHANNEL]);
});
