import asyncio
import json
from datetime import datetime, timedelta, timezone

import pytest
from redis.exceptions import ConnectionError

from shared.metrics import (
    REDIS_SNAPSHOT_RECONCILIATION_TOTAL,
    REDIS_SNAPSHOT_VERSION_LAG,
)
from shared.services.dashboard_snapshot import DashboardSnapshotClient
from shared.services.dashboard_snapshot.client import (
    INVALIDATION_CHANNEL,
    SNAPSHOT_KEY,
)


def snapshot_json(epoch=1, version=1, generated_at=None):
    return json.dumps({
        "epoch": epoch,
        "version": version,
        "generatedAt": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "buildings": [
            {
                "id": "507f1f77bcf86cd799439011",
                "name": {"uk": "Будинок", "en": "Building"},
                "color": "#fff",
                "order": 1,
                "hasBoundStation": True,
                "chargeSource": "None",
            }
        ],
        "config": {"title": {"uk": "Панель", "en": "Dashboard"}},
        "outagesSchedules": {},
    })


class FakePubSub:
    def __init__(self, fail_on_listen=False):
        self.messages = asyncio.Queue()
        self.channels = []
        self.closed = False
        self.fail_on_listen = fail_on_listen

    async def subscribe(self, channel):
        self.channels.append(channel)

    async def listen(self):
        if self.fail_on_listen:
            raise ConnectionError("simulated disconnect")
        yield {"type": "subscribe"}
        while True:
            yield await self.messages.get()

    async def aclose(self):
        self.closed = True


class FakeRedis:
    def __init__(self, value, fail_first_subscriber=False):
        self.value = value
        self.pubsubs = []
        self.fail_first_subscriber = fail_first_subscriber

    def pubsub(self):
        pubsub = FakePubSub(
            fail_on_listen=self.fail_first_subscriber and not self.pubsubs
        )
        self.pubsubs.append(pubsub)
        return pubsub

    async def get(self, key):
        assert key == SNAPSHOT_KEY
        return self.value


class FakeResponse:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self):
        self.requests = []

    def post(self, url, **kwargs):
        self.requests.append((url, kwargs))
        return FakeResponse()


@pytest.mark.asyncio
async def test_subscribes_before_loading_and_exposes_snapshot():
    redis = FakeRedis(snapshot_json())
    client = DashboardSnapshotClient(redis, FakeSession(), "http://refresh")

    await client.start()
    try:
        assert redis.pubsubs[0].channels == [INVALIDATION_CHANNEL]
        assert client.get_snapshot() is not None
        assert client.get_building("507f1f77bcf86cd799439011").name.root["en"] == "Building"
        assert client.get_config().title.root["uk"] == "Панель"
        assert client.get_outages_schedule("queue") is None
        assert (client.epoch, client.version) == (1, 1)
        assert client.is_subscribed
        assert client.health()["status"] == "healthy"
    finally:
        await client.stop()
    assert redis.pubsubs[0].closed


@pytest.mark.asyncio
async def test_version_lag_metric_reflects_adopted_snapshot():
    client = DashboardSnapshotClient(
        FakeRedis(snapshot_json(epoch=3, version=7)),
        FakeSession(),
        "http://refresh",
    )

    await client.start()
    try:
        assert (client.redis_epoch, client.redis_version) == (3, 7)
        assert (client.epoch, client.version) == (3, 7)
        assert REDIS_SNAPSHOT_VERSION_LAG._value.get() == 0
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_health_does_not_mutate_reconciliation_lag_state():
    client = DashboardSnapshotClient(
        FakeRedis(snapshot_json(epoch=3, version=7)),
        FakeSession(),
        "http://refresh",
    )

    await client.start()
    try:
        client._version_lag_since = 123.0
        assert client.health()["versionLag"] == 0
        assert client._version_lag_since == 123.0
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_notification_loads_only_newer_snapshot():
    redis = FakeRedis(snapshot_json(epoch=1, version=1))
    client = DashboardSnapshotClient(redis, FakeSession(), "http://refresh")
    await client.start()
    try:
        redis.value = snapshot_json(epoch=2, version=1)
        await redis.pubsubs[0].messages.put({
            "type": "message",
            "data": json.dumps({"key": SNAPSHOT_KEY, "epoch": 2, "version": 1}),
        })
        await asyncio.wait_for(_wait_for_version(client, 2, 1), timeout=1)

        redis.value = snapshot_json(epoch=1, version=100)
        await client.reconcile()
        assert (client.epoch, client.version) == (2, 1)
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_reconnect_resubscribes_and_reloads_snapshot():
    redis = FakeRedis(snapshot_json(epoch=1, version=1), fail_first_subscriber=True)
    client = DashboardSnapshotClient(redis, FakeSession(), "http://refresh")
    await client.start()
    try:
        redis.value = snapshot_json(epoch=2, version=1)
        await asyncio.wait_for(_wait_for_version(client, 2, 1), timeout=3)
        assert len(redis.pubsubs) >= 2
        assert client.is_subscribed
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_cache_miss_requests_refresh_and_stays_empty_without_snapshot():
    session = FakeSession()
    client = DashboardSnapshotClient(
        FakeRedis(None),
        session,
        "http://refresh",
        refresh_wait_seconds=0,
    )

    await client.start()
    try:
        assert len(session.requests) == 1
        url, request = session.requests[0]
        assert url == "http://refresh"
        assert request["json"] == {
            "reason": "cache-miss",
            "requestedBy": "shared-consumer",
        }
        assert request["timeout"].total == 5
        assert client.get_snapshot() is None
        assert client.is_stale
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_stale_snapshot_reports_age():
    generated_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    client = DashboardSnapshotClient(
        FakeRedis(snapshot_json(generated_at=generated_at)),
        FakeSession(),
        "http://refresh",
        stale_threshold_seconds=1,
    )

    await client.start()
    try:
        assert client.is_stale
        assert client.age_seconds >= 10
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_health_is_unhealthy_at_configured_stale_threshold():
    generated_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    client = DashboardSnapshotClient(
        FakeRedis(snapshot_json(generated_at=generated_at)),
        FakeSession(),
        "http://refresh",
        stale_threshold_seconds=1,
    )

    await client.start()
    try:
        assert client.health()["isStale"] is True
        assert client.health()["status"] == "unhealthy"
    finally:
        await client.stop()


@pytest.mark.asyncio
async def test_later_cache_misses_request_rate_limited_refresh(monkeypatch):
    monkeypatch.setattr(
        "shared.services.dashboard_snapshot.client.CACHE_MISS_REFRESH_COOLDOWN_SECONDS",
        0.02,
    )
    redis = FakeRedis(snapshot_json())
    session = FakeSession()
    client = DashboardSnapshotClient(
        redis,
        session,
        "http://refresh",
        reconciliation_interval_seconds=0.005,
        refresh_wait_seconds=0,
    )
    miss_count = REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(
        result="miss"
    )._value.get()

    await client.start()
    try:
        redis.value = None
        await asyncio.sleep(0.06)

        assert 2 <= len(session.requests) < 5
        assert (
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="miss")._value.get()
            > miss_count
        )
    finally:
        await client.stop()


async def _wait_for_version(client, epoch, version):
    while (client.epoch, client.version) != (epoch, version):
        await asyncio.sleep(0.01)
