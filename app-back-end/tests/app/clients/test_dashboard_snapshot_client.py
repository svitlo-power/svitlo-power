"""Tests for DashboardSnapshotClient."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from app.clients.dashboard_snapshot_client import (
    DashboardSnapshotClient,
    SNAPSHOT_KEY,
    INVALIDATION_CHANNEL,
)
from app.clients.snapshot_models import (
    DashboardSnapshot,
    BuildingSnapshot,
    ConfigSnapshot,
    UnitScheduleSnapshot,
    DayScheduleSnapshot,
    SlotSnapshot,
    LocalizableValue,
)


@pytest.fixture
def mock_redis():
    redis_mock = AsyncMock(spec=redis.Redis)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.pubsub.return_value = AsyncMock()
    return redis_mock


@pytest.fixture
def snapshot_client(mock_redis):
    return DashboardSnapshotClient(mock_redis)


@pytest.fixture
def sample_snapshot():
    return DashboardSnapshot(
        epoch=1700000000000,
        version=42,
        generated_at=datetime.now(timezone.utc),
        buildings=[
            BuildingSnapshot(
                id="64a1b2c3d4e5f6a7b8c9d0e1",
                name={"en": "Test Building", "uk": "\u0422\u0435\u0441\u0442\u043e\u0432\u0438\u0439 \u0431\u0443\u0434\u0438\u043d\u043e\u043a"},
                color="#FF0000",
                order=1,
                has_bound_station=True,
                is_grid_available=True,
                grid_availability_pct=100,
                has_mixed_reporter_states=False,
                is_charging=True,
                is_discharging=False,
                is_offline=False,
                battery_percent=85.0,
                consumption_power="1.5 kW",
                battery_discharge_time="5h",
                battery_charge_time="3h",
                charge_source="Grid",
                charge_power=1500.0,
            )
        ],
        config=ConfigSnapshot(
            title={"en": "Dashboard", "uk": "\u041f\u0430\u043d\u0435\u043b\u044c"},
            outages_schedule={
                "enable": True,
                "regionId": 1,
                "dsoId": 1,
                "queue": "queue_1",
            },
        ),
        outages_schedules={
            "queue_1": UnitScheduleSnapshot(
                days=[
                    DayScheduleSnapshot(
                        slots=[
                            SlotSnapshot(start=0, end=24, type="Definite"),
                        ],
                        date=datetime.now(timezone.utc),
                        status="ScheduleApplies",
                    )
                ],
                updatedOn=datetime.now(timezone.utc),
            )
        },
    )


class TestDashboardSnapshotClientInit:
    def test_init_stores_dependencies(self, mock_redis):
        client = DashboardSnapshotClient(mock_redis)
        assert client._redis == mock_redis
        assert client._snapshot is None
        assert client._local_epoch is None
        assert client._local_version is None
        assert client._subscribed is False

    def test_epoch_property_none_initially(self, snapshot_client):
        assert snapshot_client.epoch is None

    def test_version_property_none_initially(self, snapshot_client):
        assert snapshot_client.version is None

    def test_is_stale_true_when_no_snapshot(self, snapshot_client):
        assert snapshot_client.is_stale is True

    def test_age_seconds_inf_when_no_snapshot(self, snapshot_client):
        assert snapshot_client.age_seconds == float("inf")

    def test_get_snapshot_none_initially(self, snapshot_client):
        assert snapshot_client.get_snapshot() is None

    def test_get_buildings_empty_initially(self, snapshot_client):
        assert snapshot_client.get_buildings() == []

    def test_get_building_none_initially(self, snapshot_client):
        assert snapshot_client.get_building("abc") is None

    def test_get_config_none_initially(self, snapshot_client):
        assert snapshot_client.get_config() is None

    def test_get_outages_schedule_none_initially(self, snapshot_client):
        assert snapshot_client.get_outages_schedule("queue_1") is None


class TestDashboardSnapshotClientUpdate:
    def test_update_local_sets_fields(self, snapshot_client, sample_snapshot):
        snapshot_client._update_local(sample_snapshot)
        assert snapshot_client._snapshot == sample_snapshot
        assert snapshot_client._local_epoch == sample_snapshot.epoch
        assert snapshot_client._local_version == sample_snapshot.version

    def test_is_newer_when_no_local(self, snapshot_client):
        assert snapshot_client._is_newer(1, 1) is True

    def test_is_newer_when_epoch_higher(self, snapshot_client):
        snapshot_client._local_epoch = 100
        snapshot_client._local_version = 1
        assert snapshot_client._is_newer(200, 1) is True

    def test_is_newer_when_same_epoch_higher_version(self, snapshot_client):
        snapshot_client._local_epoch = 100
        snapshot_client._local_version = 5
        assert snapshot_client._is_newer(100, 10) is True

    def test_is_not_newer_when_same(self, snapshot_client):
        snapshot_client._local_epoch = 100
        snapshot_client._local_version = 5
        assert snapshot_client._is_newer(100, 5) is False

    def test_is_not_newer_when_lower(self, snapshot_client):
        snapshot_client._local_epoch = 100
        snapshot_client._local_version = 5
        assert snapshot_client._is_newer(99, 100) is False

    def test_is_newer_epoch_change_accepts_lower_version(self, snapshot_client):
        """Epoch change: accept lower version when epoch increases."""
        snapshot_client._local_epoch = 100
        snapshot_client._local_version = 50
        assert snapshot_client._is_newer(200, 1) is True


class TestDashboardSnapshotClientGetBuilding:
    def test_get_building_found(self, snapshot_client, sample_snapshot):
        snapshot_client._update_local(sample_snapshot)
        result = snapshot_client.get_building("64a1b2c3d4e5f6a7b8c9d0e1")
        assert result is not None
        assert result.id == "64a1b2c3d4e5f6a7b8c9d0e1"

    def test_get_building_not_found(self, snapshot_client, sample_snapshot):
        snapshot_client._update_local(sample_snapshot)
        result = snapshot_client.get_building("nonexistent")
        assert result is None

    def test_get_outages_schedule_found(self, snapshot_client, sample_snapshot):
        snapshot_client._update_local(sample_snapshot)
        result = snapshot_client.get_outages_schedule("queue_1")
        assert result is not None

    def test_get_outages_schedule_not_found(self, snapshot_client, sample_snapshot):
        snapshot_client._update_local(sample_snapshot)
        result = snapshot_client.get_outages_schedule("nonexistent")
        assert result is None


class TestDashboardSnapshotClientStartStop:
    @pytest.mark.asyncio
    async def test_start_subscribes_and_loads(self, snapshot_client, mock_redis, sample_snapshot):
        mock_redis.get.return_value = sample_snapshot.model_dump_json(by_alias=True)
        pubsub_mock = AsyncMock()
        mock_redis.pubsub.return_value = pubsub_mock

        await snapshot_client.start()

        assert snapshot_client._subscribed is True
        pubsub_mock.subscribe.assert_called_once_with(INVALIDATION_CHANNEL)
        mock_redis.get.assert_called_with(SNAPSHOT_KEY)
        assert snapshot_client._snapshot == sample_snapshot

        await snapshot_client.stop()
        assert snapshot_client._subscribed is False

    @pytest.mark.asyncio
    async def test_start_cache_miss(self, snapshot_client, mock_redis):
        mock_redis.get.return_value = None
        pubsub_mock = AsyncMock()
        mock_redis.pubsub.return_value = pubsub_mock

        with patch.object(snapshot_client, '_handle_cache_miss', new_callable=AsyncMock) as mock_miss:
            await snapshot_client.start()
            mock_miss.assert_called_once()

        await snapshot_client.stop()


class TestDashboardSnapshotClientReconcile:
    @pytest.mark.asyncio
    async def test_reconcile_updates_when_newer(self, snapshot_client, mock_redis, sample_snapshot):
        snapshot_client._local_epoch = 100
        snapshot_client._local_version = 1
        mock_redis.get.return_value = sample_snapshot.model_dump_json(by_alias=True)

        await snapshot_client._reconcile()

        assert snapshot_client._local_epoch == sample_snapshot.epoch
        assert snapshot_client._local_version == sample_snapshot.version

    @pytest.mark.asyncio
    async def test_reconcile_no_update_when_stale(self, snapshot_client, mock_redis, sample_snapshot):
        snapshot_client._local_epoch = sample_snapshot.epoch
        snapshot_client._local_version = sample_snapshot.version + 10
        mock_redis.get.return_value = sample_snapshot.model_dump_json(by_alias=True)

        await snapshot_client._reconcile()

        assert snapshot_client._local_version == sample_snapshot.version + 10

    @pytest.mark.asyncio
    async def test_reconcile_cache_miss(self, snapshot_client, mock_redis):
        mock_redis.get.return_value = None
        with patch.object(snapshot_client, '_handle_cache_miss', new_callable=AsyncMock) as mock_miss:
            await snapshot_client._reconcile()
            mock_miss.assert_called_once()


class TestDashboardSnapshotClientIsStale:
    def test_is_stale_false_when_fresh(self, snapshot_client, sample_snapshot):
        snapshot_client._update_local(sample_snapshot)
        assert snapshot_client.is_stale is False

    def test_is_stale_true_when_no_snapshot(self, snapshot_client):
        assert snapshot_client.is_stale is True
