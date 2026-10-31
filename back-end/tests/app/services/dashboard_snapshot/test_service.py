"""Tests for DashboardSnapshotService."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.asyncio import Redis

from app.services.dashboard_snapshot.service import (
    DashboardSnapshotService,
    SNAPSHOT_KEY,
    INVALIDATION_CHANNEL,
    LEASE_KEY,
    EPOCH_KEY,
    VERSION_COMMITTED_KEY,
    VERSION_NEXT_KEY,
    LUA_WRITE_SCRIPT,
)
from app.services.dashboard_snapshot.models import (
    DashboardSnapshot,
    ConfigSnapshot,
    LocalizableValue,
)
from shared.features import feature_flags, FeatureFlag


class TestDashboardSnapshotServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        assert service._events is mock_events
        assert service._dashboard is mock_dashboard
        assert service._lease_token is None
        assert service._epoch is None
        assert service._version is None


class TestBuildSnapshot:
    @pytest.mark.asyncio
    async def test_build_snapshot_returns_valid_model(self):
        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard.get_config = AsyncMock(
            return_value=MagicMock(
                title=LocalizableValue(uk="\u041f\u0430\u043d\u0435\u043b", en="Dashboard"),
                outages_schedule=None,
            )
        )
        mock_dashboard.get_buildings_with_summary = AsyncMock(return_value=[])
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_outages_repo.get_all_schedules = AsyncMock(
            return_value=MagicMock(root={})
        )
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        service._epoch = 1700000000000
        service._version = 1

        snapshot = await service.build_snapshot()

        assert isinstance(snapshot, DashboardSnapshot)
        assert snapshot.epoch == 1700000000000
        assert snapshot.version == 1
        assert snapshot.buildings == []
        assert snapshot.config.title.en == "Dashboard"
        assert snapshot.outages_schedules == {}


class TestPublishSnapshot:
    @pytest.mark.asyncio
    async def test_publish_snapshot_no_lease(self):
        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        service._lease_token = None

        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[],
            config=ConfigSnapshot(
                title=LocalizableValue(uk="\u0422\u0435\u0441\u0442", en="Test"),
                outages_schedule=None,
            ),
            outages_schedules={},
        )

        result = await service.publish_snapshot(snapshot)
        assert result is False

    @pytest.mark.asyncio
    async def test_publish_snapshot_disabled(self):
        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        service._lease_token = "test-lease-token"

        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, False)

        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[],
            config=ConfigSnapshot(
                title=LocalizableValue(uk="\u0422\u0435\u0441\u0442", en="Test"),
                outages_schedule=None,
            ),
            outages_schedules={},
        )

        result = await service.publish_snapshot(snapshot)
        assert result is True

        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)

    @pytest.mark.asyncio
    async def test_publish_snapshot_success(self):
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.eval = AsyncMock(return_value=[1, "ok", "epoch=1700000000000,version=1"])

        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        service._redis = mock_redis
        service._lease_token = "test-lease-token"
        service._epoch = 1700000000000
        service._version = 1

        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[],
            config=ConfigSnapshot(
                title=LocalizableValue(uk="\u0422\u0435\u0441\u0442", en="Test"),
                outages_schedule=None,
            ),
            outages_schedules={},
        )

        result = await service.publish_snapshot(snapshot)
        assert result is True
        mock_redis.eval.assert_called_once()
        call_args = mock_redis.eval.call_args
        assert call_args[0][0] == LUA_WRITE_SCRIPT
        assert call_args[0][1] == 5
        assert SNAPSHOT_KEY in call_args[0][2:7]
        assert LEASE_KEY in call_args[0][2:7]

    @pytest.mark.asyncio
    async def test_publish_snapshot_rejected_stale_version(self):
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.eval = AsyncMock(return_value=[0, "version-stale", "expected-version 1 <= current 2"])

        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        service._redis = mock_redis
        service._lease_token = "test-lease-token"
        service._epoch = 1700000000000
        service._version = 1

        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[],
            config=ConfigSnapshot(
                title=LocalizableValue(uk="\u0422\u0435\u0441\u0442", en="Test"),
                outages_schedule=None,
            ),
            outages_schedules={},
        )

        result = await service.publish_snapshot(snapshot)
        assert result is False


class TestHandleRefreshRequest:
    @pytest.mark.asyncio
    async def test_handle_refresh_request_success(self):
        mock_redis = AsyncMock(spec=Redis)
        mock_redis.eval = AsyncMock(return_value=[1, "ok", "epoch=1700000000000,version=1"])

        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard.get_config = AsyncMock(
            return_value=MagicMock(
                title=LocalizableValue(uk="\u041f\u0430\u043d\u0435\u043b", en="Dashboard"),
                outages_schedule=None,
            )
        )
        mock_dashboard.get_buildings_with_summary = AsyncMock(return_value=[])
        mock_dashboard_repo = MagicMock()
        mock_stations = MagicMock()
        mock_stations_data = MagicMock()
        mock_ext_data = MagicMock()
        mock_users = MagicMock()
        mock_outages_schedule = MagicMock()
        mock_outages_repo = MagicMock()
        mock_outages_repo.get_all_schedules = AsyncMock(return_value=MagicMock(root={}))
        mock_settings = MagicMock()

        service = DashboardSnapshotService(
            mock_events,
            mock_dashboard,
            mock_dashboard_repo,
            mock_stations,
            mock_stations_data,
            mock_ext_data,
            mock_users,
            mock_outages_schedule,
            mock_outages_repo,
            mock_settings,
            "redis://localhost:6379",
        )
        service._redis = mock_redis
        service._lease_token = "test-lease-token"
        service._epoch = 1700000000000
        service._version = 1

        result = await service.handle_refresh_request(reason="cache-miss", requested_by="test-client")

        assert result["accepted"] is True
        assert result["epoch"] == 1700000000000
        assert result["version"] == 1
        assert result["coalesced"] is False
