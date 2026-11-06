"""Tests for DashboardSnapshotService."""



import asyncio

import json

from datetime import datetime, timezone
from types import SimpleNamespace
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

from shared.models.dashboard_snapshot import (
    BuildingSnapshot,
    ConfigSnapshot,
    DashboardSnapshot,
)
from shared.models.api.dashboard import ChargeSource
from shared.models.dashboard_config import OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue
from shared.models.outages_schedule import UnitSchedule
from shared.features import feature_flags, FeatureFlag





class _MockSettings:

    REDIS_URI = "redis://localhost:6379"





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

        mock_settings = _MockSettings()



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

        )

        assert service._events is mock_events

        assert service._lease_token is None

        assert service._epoch is None

        assert service._version is None





class TestBuildSnapshot:
    @pytest.mark.asyncio
    async def test_init_version_keys_preserves_newer_epoch_after_clock_rollback(self):
        service = DashboardSnapshotService(
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            _MockSettings(),
        )
        service._epoch = 100
        previous_snapshot = DashboardSnapshot(
            epoch=300,
            version=8,
            generated_at=datetime.now(timezone.utc),
            buildings=[],
            config=ConfigSnapshot(title={"en": "Dashboard", "uk": "Панель"}),
            outages_schedules={},
        )
        redis_values = {
            EPOCH_KEY: "200",
            SNAPSHOT_KEY: previous_snapshot.model_dump_json(by_alias=True),
        }
        service._redis = AsyncMock(spec=Redis)
        service._redis.get = AsyncMock(side_effect=lambda key: redis_values.get(key))
        service._redis.set = AsyncMock()

        await service._init_version_keys()

        assert service._epoch == 300
        service._redis.set.assert_any_await(EPOCH_KEY, 300)

    @pytest.mark.asyncio
    async def test_build_snapshot_returns_valid_model(self):

        mock_events = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard.get_config = AsyncMock()
        title = LocalizableValue(
            {"uk": "\u041f\u0430\u043d\u0435\u043b", "en": "Dashboard"}
        )
        configured_schedule = OutagesScheduleConfig(
            enable=True,
            region_id=25,
            dso_id=902,
            queue="queue1",
        )
        mock_dashboard.get_config.return_value = SimpleNamespace(
            title=title,
            outages_schedule=configured_schedule,
        )
        building = SimpleNamespace(
            id="507f1f77bcf86cd799439011",
            name=LocalizableValue({"en": "Building", "uk": "Будинок"}),
            color="#fff",
            order=1,
            has_bound_station=True,
            is_grid_available=True,
            grid_availability_pct=100,
            has_mixed_reporter_states=False,
            is_charging=True,
            is_discharging=False,
            is_offline=False,
            battery_percent=25,
            consumption_power="1.00",
            battery_discharge_time=None,
            battery_charge_time=None,
            charge_source=ChargeSource.GRID,
            charge_power=500,
        )
        mock_dashboard.get_buildings_with_summary = AsyncMock(return_value=[building])

        mock_dashboard_repo = MagicMock()

        mock_stations = MagicMock()

        mock_stations_data = MagicMock()

        mock_ext_data = MagicMock()

        mock_users = MagicMock()

        mock_outages_schedule = MagicMock()

        mock_outages_repo = MagicMock()

        unit_schedule = UnitSchedule(
            days=[],
            updatedOn=datetime(2026, 10, 31, tzinfo=timezone.utc),
        )
        mock_outages_repo.get_all_schedules = AsyncMock(
            return_value=MagicMock(root={"queue1": unit_schedule})
        )

        mock_settings = _MockSettings()



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

        )

        service._epoch = 1700000000000

        service._version = 1



        snapshot = await service.build_snapshot()



        assert isinstance(snapshot, DashboardSnapshot)
        assert snapshot.epoch == 1700000000000
        assert snapshot.version == 1
        assert snapshot.buildings[0].charge_source == "Grid"
        assert snapshot.config.title is title
        assert snapshot.config.outages_schedule is configured_schedule
        assert snapshot.outages_schedules["queue1"] is unit_schedule


class TestRefreshAndPublish:
    @pytest.mark.asyncio
    async def test_broadcasts_dashboard_updated_after_snapshot_is_published(self):
        order = []
        events = MagicMock()
        events.broadcast_public = AsyncMock(
            side_effect=lambda event, data: order.append(("broadcast", event, data))
        )
        service = DashboardSnapshotService(
            events,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            _MockSettings(),
        )
        service._redis = AsyncMock(spec=Redis)
        service._redis.incr = AsyncMock(return_value=2)
        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=2,
            generated_at=datetime.now(timezone.utc),
            buildings=[],
            config=ConfigSnapshot(title={"uk": "Панель", "en": "Dashboard"}),
            outages_schedules={},
        )
        service.build_snapshot = AsyncMock(return_value=snapshot)

        async def publish(_snapshot):
            order.append(("publish", _snapshot.version))
            return True

        service.publish_snapshot = AsyncMock(side_effect=publish)

        await service.refresh_and_publish()

        assert order == [
            ("publish", 2),
            (
                "broadcast",
                "dashboard_updated",
                {"changed": ["buildings", "summary", "config", "outages"]},
            ),
        ]

    def test_changed_sections_reports_only_changed_building_summary(self):
        building = BuildingSnapshot(
            id="507f1f77bcf86cd799439011",
            name={"en": "Building", "uk": "Будинок"},
            color="#fff",
            order=1,
            has_bound_station=True,
            battery_percent=25,
            charge_source="Grid",
        )
        updated_building = building.model_copy(update={"battery_percent": 30})
        config = ConfigSnapshot(title={"en": "Dashboard", "uk": "Панель"})
        previous = DashboardSnapshot(
            epoch=1,
            version=1,
            generated_at=datetime.now(timezone.utc),
            buildings=[building],
            config=config,
            outages_schedules={},
        )
        current = previous.model_copy(
            update={"version": 2, "buildings": [updated_building]}
        )

        assert DashboardSnapshotService._changed_sections(previous, current) == [
            "summary"
        ]

    def test_changed_sections_reports_building_order_and_config_changes(self):
        building = BuildingSnapshot(
            id="507f1f77bcf86cd799439011",
            name={"en": "Building", "uk": "Будинок"},
            color="#fff",
            order=1,
            has_bound_station=True,
            charge_source="None",
        )
        previous = DashboardSnapshot(
            epoch=1,
            version=1,
            generated_at=datetime.now(timezone.utc),
            buildings=[building],
            config=ConfigSnapshot(title={"en": "Dashboard", "uk": "Панель"}),
            outages_schedules={},
        )
        current = previous.model_copy(
            update={
                "version": 2,
                "buildings": [building.model_copy(update={"order": 2})],
                "config": ConfigSnapshot(title={"en": "New", "uk": "Нова"}),
            }
        )

        assert DashboardSnapshotService._changed_sections(previous, current) == [
            "buildings",
            "config",
        ]


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

        mock_settings = _MockSettings()



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

        )

        service._lease_token = None



        snapshot = DashboardSnapshot(

            epoch=1700000000000,

            version=1,

            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),

            buildings=[],

            config=ConfigSnapshot(

                title={"uk": "\u0422\u0435\u0441\u0442", "en": "Test"},

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

        mock_settings = _MockSettings()



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

        )

        service._lease_token = "test-lease-token"



        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, False)



        snapshot = DashboardSnapshot(

            epoch=1700000000000,

            version=1,

            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),

            buildings=[],

            config=ConfigSnapshot(

                title={"uk": "\u0422\u0435\u0441\u0442", "en": "Test"},

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

        mock_settings = _MockSettings()



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

                title={"uk": "\u0422\u0435\u0441\u0442", "en": "Test"},

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

        mock_settings = _MockSettings()



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

                title={"uk": "\u0422\u0435\u0441\u0442", "en": "Test"},

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
        mock_events.broadcast_public = AsyncMock()

        mock_dashboard = MagicMock()

        mock_dashboard.get_config = AsyncMock()

        mock_dashboard.get_config.return_value.title = {

            "uk": "\u041f\u0430\u043d\u0435\u043b",

            "en": "Dashboard",

        }

        mock_dashboard.get_config.return_value.outages_schedule = None

        mock_dashboard.get_buildings_with_summary = AsyncMock(return_value=[])

        mock_dashboard_repo = MagicMock()

        mock_stations = MagicMock()

        mock_stations_data = MagicMock()

        mock_ext_data = MagicMock()

        mock_users = MagicMock()

        mock_outages_schedule = MagicMock()

        mock_outages_repo = MagicMock()

        mock_outages_repo.get_all_schedules = AsyncMock(return_value=MagicMock(root={}))

        mock_settings = _MockSettings()



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

        )

        service._redis = mock_redis
        mock_redis.incr = AsyncMock(return_value=1)

        service._lease_token = "test-lease-token"

        service._epoch = 1700000000000

        service._version = 1


        result = await service.handle_refresh_request(reason="cache-miss", requested_by="test-client")



        assert result["accepted"] is True

        assert result["epoch"] == 1700000000000

        assert result["version"] == 1

        assert result["coalesced"] is False
