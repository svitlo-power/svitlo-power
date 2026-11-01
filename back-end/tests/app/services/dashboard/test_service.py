"""Tests for app/services/dashboard/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.dashboard.service import DashboardService
from shared.models import (
    BuildingResponse,
    BuildingSummaryResponse,
    DashboardConfigResponse,
    SaveBuildingRequest,
    SaveDashboardConfigRequest,
    ChargeSource,
)
from shared.models.building import Building
from shared.models.localizable_value import LocalizableValue
from shared.models.station import Station
from shared.models.station_data import StationData
from shared.models.ext_data import ExtData
from shared.models.user import User
from shared.features import feature_flags, FeatureFlag


class TestDashboardServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo,
            mock_settings
        )
        assert service._dashboard is mock_dashboard_repo
        assert service._ext_data is mock_ext_data_repo
        assert service._stations is mock_stations_repo
        assert service._stations_data is mock_stations_data_repo
        assert service._users is mock_users_repo


class TestDashboardServiceGetConfig:
    @pytest.mark.asyncio
    async def test_get_config_returns_response(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        mock_settings.get_localizable_text = AsyncMock(
            return_value=LocalizableValue({"en": "My Dashboard"})
        )
        mock_settings.get_boolean = AsyncMock(return_value=True)
        mock_settings.get_value = AsyncMock(side_effect=[25, 902])
        mock_settings.get_text = AsyncMock(return_value="queue1")
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        result = await service.get_config()
        assert isinstance(result, DashboardConfigResponse)
        assert result.enable_outages_schedule is True
        assert result.outages_schedule_queue == "queue1"
        assert result.outages_schedule.region_id == 25
        assert result.outages_schedule.dso_id == 902


class TestDashboardServiceSaveConfig:
    @pytest.mark.asyncio
    async def test_save_config_updates_settings_and_broadcasts(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        mock_settings.bulk_update = AsyncMock(return_value={
            "dashboard_title": True,
            "dashboard_outages_schedule_enabled": True,
            "dashboard_outages_schedule_region": True,
            "dashboard_outages_schedule_dso": True,
            "dashboard_outages_schedule_queue": True,
        })
        mock_settings.get_localizable_text = AsyncMock(
            return_value=LocalizableValue({"en": "Test"})
        )
        mock_settings.get_boolean = AsyncMock(return_value=True)
        mock_settings.get_value = AsyncMock(side_effect=[25, 902])
        mock_settings.get_text = AsyncMock(return_value="queue1")
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        request = SaveDashboardConfigRequest(
            title=LocalizableValue({"en": "Test"}),
            outagesSchedule={
                "enable": True,
                "regionId": 25,
                "dsoId": 902,
                "queue": "queue1",
            },
        )
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)
        result = await service.save_config(request)
        assert isinstance(result, DashboardConfigResponse)
        mock_settings.bulk_update.assert_awaited_once()
        updates = mock_settings.bulk_update.call_args.args[0]
        assert updates["dashboard_title"] == LocalizableValue({"en": "Test"})
        assert updates["dashboard_outages_schedule_enabled"] is True
        assert updates["dashboard_outages_schedule_region"] == 25
        assert updates["dashboard_outages_schedule_dso"] == 902
        assert updates["dashboard_outages_schedule_queue"] == "queue1"
        mock_events.broadcast_public.assert_called_once_with("dashboard_config_updated", None)

    @pytest.mark.asyncio
    async def test_save_config_fails_when_a_setting_cannot_be_updated(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_settings = AsyncMock()
        mock_settings.bulk_update = AsyncMock(return_value={
            "dashboard_title": True,
            "dashboard_outages_schedule_enabled": False,
        })
        service = DashboardService(mock_events, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), mock_settings)
        request = SaveDashboardConfigRequest(
            title=LocalizableValue({"en": "Test"}),
            enableOutagesSchedule=False,
        )
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)

        with pytest.raises(RuntimeError, match="Unable to save dashboard settings"):
            await service.save_config(request)

        mock_settings.bulk_update.assert_awaited_once()
        mock_events.broadcast_public.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_disabling_schedule_preserves_existing_selection(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_settings = AsyncMock()
        mock_settings.bulk_update = AsyncMock(return_value={
            "dashboard_title": True,
            "dashboard_outages_schedule_enabled": True,
        })
        mock_settings.get_localizable_text = AsyncMock(
            return_value=LocalizableValue({"en": "Test"})
        )
        mock_settings.get_boolean = AsyncMock(return_value=False)
        mock_settings.get_value = AsyncMock(side_effect=["Kyiv", "Yasno"])
        mock_settings.get_text = AsyncMock(return_value="queue1")
        service = DashboardService(mock_events, MagicMock(), MagicMock(), MagicMock(), MagicMock(), MagicMock(), mock_settings)
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)

        await service.save_config(SaveDashboardConfigRequest(
            title=LocalizableValue({"en": "Test"}),
            outagesSchedule={
                "enable": False,
                "regionId": None,
                "dsoId": None,
                "queue": None,
            },
        ))

        assert mock_settings.bulk_update.call_args.args[0] == {
            "dashboard_title": LocalizableValue({"en": "Test"}),
            "dashboard_outages_schedule_enabled": False,
        }


class TestDashboardServiceProcessBuilding:
    def test_process_building_returns_response(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)

        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)

        building = Building(
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            enabled=True,
            order=1,
        )
        result = service._process_building(building)
        assert isinstance(result, BuildingResponse)
        assert result.name.root == {"en": "Building 1"}
        assert result.color == "#FF0000"
        assert result.has_bound_station is False
        assert result.order == 1


class TestDashboardServiceGetBuildings:
    @pytest.mark.asyncio
    async def test_get_buildings_returns_list(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        buildings = [
            Building(name=LocalizableValue({"en": "B1"}), color="#FF0000", enabled=True, order=1),
            Building(name=LocalizableValue({"en": "B2"}), color="#00FF00", enabled=True, order=2),
        ]
        mock_dashboard_repo.get_buildings = AsyncMock(return_value=buildings)

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        result = await service.get_buildings(all=True)
        assert len(result) == 2
        assert isinstance(result[0], BuildingResponse)
        assert result[0].name.root == {"en": "B1"}


class TestDashboardServiceGetBuilding:
    @pytest.mark.asyncio
    async def test_get_building_returns_edit_response(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = Building(
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            enabled=True,
            order=1,
        )
        mock_dashboard_repo.get_building = AsyncMock(return_value=building)

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        result = await service.get_building(PydanticObjectId())
        assert result is not None
        assert result.name.root == {"en": "Building 1"}

    @pytest.mark.asyncio
    async def test_get_building_not_found_returns_none(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_dashboard_repo.get_building = AsyncMock(return_value=None)

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        result = await service.get_building(PydanticObjectId())
        assert result is None


class TestDashboardServiceCreateBuilding:
    @pytest.mark.asyncio
    async def test_create_building_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_dashboard_repo.create_building = AsyncMock(return_value=PydanticObjectId())

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "New Building"}),
            color="#FF0000",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=1,
        )
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)
        result = await service.create_building(request)
        assert result is not None
        mock_dashboard_repo.create_building.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("buildings_updated", None)


class TestDashboardServiceDeleteBuilding:
    @pytest.mark.asyncio
    async def test_delete_building_success(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = Building(name=LocalizableValue({"en": "Test"}), color="#FF0000", enabled=True, order=1)
        mock_dashboard_repo.get_building = AsyncMock(return_value=building)
        mock_dashboard_repo.delete_building = AsyncMock()
        mock_dashboard_repo.get_buildings = AsyncMock(return_value=[])
        mock_dashboard_repo.reorder_buildings = AsyncMock()

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)
        result = await service.delete_building(PydanticObjectId())
        assert result is True
        mock_dashboard_repo.delete_building.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("buildings_updated", None)

    @pytest.mark.asyncio
    async def test_delete_building_not_found(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_dashboard_repo.get_building = AsyncMock(return_value=None)

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        result = await service.delete_building(PydanticObjectId())
        assert result is False
        mock_dashboard_repo.delete_building.assert_not_called()


class TestDashboardServiceEditBuilding:
    @pytest.mark.asyncio
    async def test_edit_building_with_empty_report_users(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = Building(
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            enabled=True,
            order=1,
        )
        mock_dashboard_repo.get_building = AsyncMock(return_value=building)
        mock_dashboard_repo.edit_building = AsyncMock()

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "Updated Building"}),
            color="#00FF00",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=2,
        )
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)
        result = await service.edit_building(PydanticObjectId(), request)
        assert result is not None
        mock_dashboard_repo.edit_building.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("buildings_updated", None)

    @pytest.mark.asyncio
    async def test_edit_building_with_station_and_report_users(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = Building(
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            enabled=True,
            order=1,
        )
        mock_dashboard_repo.get_building = AsyncMock(return_value=building)
        mock_dashboard_repo.edit_building = AsyncMock()
        mock_stations_repo.get_station = AsyncMock(return_value=None)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=MagicMock())

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "Updated Building"}),
            color="#00FF00",
            stationId=PydanticObjectId(),
            reportUserIds=[PydanticObjectId()],
            enabled=True,
            order=2,
        )
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, True)
        result = await service.edit_building(PydanticObjectId(), request)
        assert result is not None
        mock_dashboard_repo.edit_building.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("buildings_updated", None)


class TestDashboardServiceGetPowerLogsWithData:
    @pytest.mark.asyncio
    async def test_get_power_logs_no_station(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = Building(
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            enabled=True,
            order=1,
        )
        mock_dashboard_repo.get_building = AsyncMock(return_value=building)

        mock_settings = AsyncMock()
        mock_settings.get_number = AsyncMock(return_value=25)
        service = DashboardService(mock_events, mock_dashboard_repo, mock_ext_data_repo, mock_stations_repo, mock_stations_data_repo, mock_users_repo, mock_settings)

        result = await service.get_power_logs(
            PydanticObjectId(),
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 2, tzinfo=timezone.utc),
        )
        assert result is None
