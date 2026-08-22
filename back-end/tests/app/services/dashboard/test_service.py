"""Tests for app/services/dashboard/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.dashboard.service import DashboardService
from app.models.api import (
    BuildingResponse,
    BuildingSummaryResponse,
    DashboardConfigResponse,
    SaveBuildingRequest,
    SaveDashboardConfigRequest,
    ChargeSource,
)
from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from shared.models.localizable_value import LocalizableValue
from shared.models.station import Station
from shared.models.station_data import StationData
from shared.models.ext_data import ExtData
from shared.models.user import User


class TestDashboardServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
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

        config = DashboardConfig(
            title=LocalizableValue({"en": "My Dashboard"}),
            enable_outages_schedule=True,
            outages_schedule_queue="queue1",
        )
        mock_dashboard_repo.get_config = AsyncMock(return_value=config)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_config()
        assert isinstance(result, DashboardConfigResponse)
        assert result.enable_outages_schedule is True
        assert result.outages_schedule_queue == "queue1"


class TestDashboardServiceSaveConfig:
    @pytest.mark.asyncio
    async def test_save_config_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_dashboard_repo.save_config = AsyncMock()
        mock_dashboard_repo.get_config = AsyncMock(return_value=DashboardConfig(
            title=LocalizableValue({"en": "Test"}),
            enable_outages_schedule=False,
            outages_schedule_queue=None,
        ))

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        request = SaveDashboardConfigRequest(
            title=LocalizableValue({"en": "Test"}),
            enableOutagesSchedule=True,
            outagesScheduleQueue="queue1",
        )
        result = await service.save_config(request)
        assert isinstance(result, DashboardConfigResponse)
        mock_dashboard_repo.save_config.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("dashboard_config_updated", None)


class TestDashboardServiceProcessBuilding:
    def test_process_building_returns_response(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )

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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "New Building"}),
            color="#FF0000",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=1,
        )
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "Updated Building"}),
            color="#00FF00",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=2,
        )
        result = await service.edit_building(PydanticObjectId(), request)
        assert result is not None
        mock_dashboard_repo.edit_building.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("buildings_updated", None)

    @pytest.mark.asyncio
    async def test_edit_building_not_found(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_dashboard_repo.get_building = AsyncMock(return_value=None)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "Updated Building"}),
            color="#00FF00",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=2,
        )
        result = await service.edit_building(PydanticObjectId(), request)
        assert result is None
        mock_dashboard_repo.edit_building.assert_not_called()
        mock_events.broadcast_public.assert_not_called()


class TestDashboardServiceGetBuildingsSummary:
    @pytest.mark.asyncio
    async def test_get_buildings_summary(self):
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
        mock_dashboard_repo.get_buildings = AsyncMock(return_value=[building])

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_buildings_summary([PydanticObjectId()])
        assert len(result) == 1
        assert isinstance(result[0], BuildingSummaryResponse)


class TestDashboardServiceGetPowerLogs:
    @pytest.mark.asyncio
    async def test_get_power_logs_building_not_found(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_dashboard_repo.get_building = AsyncMock(return_value=None)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_power_logs(PydanticObjectId(), datetime.now(timezone.utc), datetime.now(timezone.utc))
        assert result is None

    @pytest.mark.asyncio
    async def test_get_power_logs_no_report_users(self):
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

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_power_logs(PydanticObjectId(), datetime.now(timezone.utc), datetime.now(timezone.utc))
        assert result is None


class TestDashboardServiceComputeTotalGeneratorTime:
    @pytest.mark.asyncio
    async def test_compute_total_generator_time_no_data(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        mock_stations_data_repo.get_full_station_data_range = AsyncMock(return_value=[])

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._compute_total_generator_time("station_id", datetime.now(timezone.utc), datetime.now(timezone.utc))
        assert result == 0

    @pytest.mark.asyncio
    async def test_compute_total_generator_time_with_data(self):
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station_id = PydanticObjectId()
        data = [
            StationData(
                station_id=station_id,
                last_update_time=now - timedelta(minutes=30),
                charge_power=-300,
                generation_power=100,
                wire_power=0,
            ),
            StationData(
                station_id=station_id,
                last_update_time=now,
                charge_power=-300,
                generation_power=100,
                wire_power=0,
            ),
        ]
        mock_stations_data_repo.get_full_station_data_range = AsyncMock(return_value=data)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._compute_total_generator_time("station_id", now - timedelta(minutes=30), now)
        assert result > 0


class TestDashboardServiceProcessBuildingSummary:
    @pytest.mark.asyncio
    async def test_process_building_summary_with_station(self):
        """Test _process_building_summary with station data."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ONLINE"
        station.battery_capacity = 500.0

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = []
        building.order = 1

        station_data = StationData(
            station_id=station.id,
            battery_soc=85.0,
            charge_power=-300.0,
            discharge_power=0.0,
            consumption_power=50.0,
            generation_power=100.0,
            wire_power=0.0,
            last_update_time=now,
        )

        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=station_data)
        mock_stations_data_repo.get_assumed_connection_status = AsyncMock(return_value="ONLINE")
        mock_stations_data_repo.get_station_data_average_column = AsyncMock(return_value=50.0)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.is_charging is True
        assert result.battery_percent == 85.0

    @pytest.mark.asyncio
    async def test_process_building_summary_with_report_users(self):
        """Test _process_building_summary with report users."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ONLINE"
        station.battery_capacity = 500.0

        user1 = MagicMock()
        user1.id = PydanticObjectId()
        user2 = MagicMock()
        user2.id = PydanticObjectId()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = [user1, user2]

        ext_data1 = ExtData(user_id=user1.id, grid_state=True, received_at=now)
        ext_data2 = ExtData(user_id=user2.id, grid_state=False, received_at=now)

        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(side_effect=[ext_data1, ext_data2])
        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=None)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.is_grid_available is True
        assert result.grid_availability_pct == 50
        assert result.has_mixed_reporter_states is True

    @pytest.mark.asyncio
    async def test_process_building_summary_no_station(self):
        """Test _process_building_summary without station."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = None
        building.report_users = []

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)

    @pytest.mark.asyncio
    async def test_process_building_summary_discharging(self):
        """Test _process_building_summary with discharging station."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ONLINE"
        station.battery_capacity = 500.0

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = []

        station_data = StationData(
            station_id=station.id,
            battery_soc=85.0,
            charge_power=0.0,
            discharge_power=300.0,
            consumption_power=50.0,
            generation_power=0.0,
            wire_power=0.0,
            last_update_time=now,
        )

        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=station_data)
        mock_stations_data_repo.get_assumed_connection_status = AsyncMock(return_value="ONLINE")
        mock_stations_data_repo.get_station_data_average_column = AsyncMock(return_value=50.0)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.is_discharging is True

    @pytest.mark.asyncio
    async def test_process_building_summary_offline(self):
        """Test _process_building_summary with offline station."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ALL_OFFLINE"
        station.battery_capacity = 500.0

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = []

        station_data = StationData(
            station_id=station.id,
            battery_soc=85.0,
            charge_power=0.0,
            discharge_power=0.0,
            consumption_power=50.0,
            generation_power=0.0,
            wire_power=0.0,
            last_update_time=now,
        )

        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=station_data)
        mock_stations_data_repo.get_assumed_connection_status = AsyncMock(return_value="ONLINE")
        mock_stations_data_repo.get_station_data_average_column = AsyncMock(return_value=50.0)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.is_offline is True

    @pytest.mark.asyncio
    async def test_process_building_summary_assumed_offline(self):
        """Test _process_building_summary with assumed offline status."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ONLINE"
        station.battery_capacity = 500.0

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = []

        station_data = StationData(
            station_id=station.id,
            battery_soc=85.0,
            charge_power=0.0,
            discharge_power=0.0,
            consumption_power=50.0,
            generation_power=0.0,
            wire_power=0.0,
            last_update_time=now,
        )

        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=station_data)
        mock_stations_data_repo.get_assumed_connection_status = AsyncMock(return_value="OFFLINE")
        mock_stations_data_repo.get_station_data_average_column = AsyncMock(return_value=50.0)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.is_offline is True

    @pytest.mark.asyncio
    async def test_process_building_summary_charging_generator(self):
        """Test _process_building_summary with generator charge source."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ONLINE"
        station.battery_capacity = 500.0

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = []

        station_data = StationData(
            station_id=station.id,
            battery_soc=85.0,
            charge_power=-300.0,
            discharge_power=0.0,
            consumption_power=50.0,
            generation_power=100.0,
            wire_power=0.0,
            last_update_time=now,
        )

        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=station_data)
        mock_stations_data_repo.get_assumed_connection_status = AsyncMock(return_value="ONLINE")
        mock_stations_data_repo.get_station_data_average_column = AsyncMock(return_value=50.0)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.charge_source == ChargeSource.GENERATOR

    @pytest.mark.asyncio
    async def test_process_building_summary_charging_recuperation(self):
        """Test _process_building_summary with recuperation charge source."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        station = MagicMock()
        station.id = PydanticObjectId()
        station.connection_status = "ONLINE"
        station.battery_capacity = 500.0

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = []

        station_data = StationData(
            station_id=station.id,
            battery_soc=85.0,
            charge_power=-300.0,
            discharge_power=0.0,
            consumption_power=50.0,
            generation_power=0.0,
            wire_power=0.0,
            last_update_time=now,
        )

        mock_stations_data_repo.get_last_station_data = AsyncMock(return_value=station_data)
        mock_stations_data_repo.get_assumed_connection_status = AsyncMock(return_value="ONLINE")
        mock_stations_data_repo.get_station_data_average_column = AsyncMock(return_value=50.0)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service._process_building_summary(building, 25)
        assert isinstance(result, BuildingSummaryResponse)
        assert result.charge_source == ChargeSource.RECUPERATION


class TestDashboardServiceGetBuildingsWithSummary:
    @pytest.mark.asyncio
    async def test_get_buildings_with_summary(self):
        """Test get_buildings_with_summary returns buildings with summary."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.name = LocalizableValue({"en": "Building 1"})
        building.color = "#FF0000"
        building.station = None
        building.report_users = []
        building.order = 1

        mock_dashboard_repo.get_buildings = AsyncMock(return_value=[building])

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_buildings_with_summary()
        assert len(result) == 1


class TestDashboardServiceEditBuildingWithStation:
    @pytest.mark.asyncio
    async def test_edit_building_with_station_and_report_users(self):
        """Test edit_building with station and report users."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.name = LocalizableValue({"en": "Building 1"})
        building.color = "#FF0000"
        building.enabled = True
        building.order = 1
        building.station = None
        building.report_users = []

        mock_dashboard_repo.get_building = AsyncMock(return_value=building)
        mock_dashboard_repo.edit_building = AsyncMock()

        station = MagicMock()
        station.id = PydanticObjectId()
        mock_stations_repo.get_station = AsyncMock(return_value=station)

        user = MagicMock()
        user.id = PydanticObjectId()
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        request = SaveBuildingRequest(
            name=LocalizableValue({"en": "Updated Building"}),
            color="#00FF00",
            stationId=PydanticObjectId(),
            reportUserIds=[PydanticObjectId()],
            enabled=True,
            order=2,
        )
        result = await service.edit_building(PydanticObjectId(), request)
        assert result is not None
        mock_dashboard_repo.edit_building.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("buildings_updated", None)


class TestDashboardServiceGetPowerLogsWithData:
    @pytest.mark.asyncio
    async def test_get_power_logs_with_events(self):
        """Test get_power_logs with actual events."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(hours=1)
        end_date = now

        station = MagicMock()
        station.id = PydanticObjectId()

        user = MagicMock()
        user.id = PydanticObjectId()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = [user]

        mock_dashboard_repo.get_building = AsyncMock(return_value=building)

        ext_data = ExtData(user_id=user.id, grid_state=True, received_at=now - timedelta(minutes=30))
        mock_ext_data_repo.get_ext_data_statistics = AsyncMock(return_value=[ext_data])
        mock_ext_data_repo.get_last_ext_data_before_date = AsyncMock(return_value=ext_data)
        mock_stations_data_repo.get_full_station_data_range = AsyncMock(return_value=[])

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_power_logs(PydanticObjectId(), start_date, end_date)
        assert result is not None
        assert len(result.periods) > 0

    @pytest.mark.asyncio
    async def test_get_power_logs_no_events(self):
        """Test get_power_logs with no events (uses initial state)."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(hours=1)
        end_date = now

        station = MagicMock()
        station.id = PydanticObjectId()

        user = MagicMock()
        user.id = PydanticObjectId()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = station
        building.report_users = [user]

        mock_dashboard_repo.get_building = AsyncMock(return_value=building)

        mock_ext_data_repo.get_ext_data_statistics = AsyncMock(return_value=[])
        mock_ext_data_repo.get_last_ext_data_before_date = AsyncMock(return_value=None)
        mock_stations_data_repo.get_full_station_data_range = AsyncMock(return_value=[])

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_power_logs(PydanticObjectId(), start_date, end_date)
        assert result is not None
        assert len(result.periods) == 1

    @pytest.mark.asyncio
    async def test_get_power_logs_no_station(self):
        """Test get_power_logs without station (total_generator_seconds=0)."""
        mock_events = MagicMock()
        mock_dashboard_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()
        mock_users_repo = MagicMock()

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(hours=1)
        end_date = now

        user = MagicMock()
        user.id = PydanticObjectId()

        building = MagicMock()
        building.id = PydanticObjectId()
        building.station = None
        building.report_users = [user]

        mock_dashboard_repo.get_building = AsyncMock(return_value=building)

        ext_data = ExtData(user_id=user.id, grid_state=True, received_at=now - timedelta(minutes=30))
        mock_ext_data_repo.get_ext_data_statistics = AsyncMock(return_value=[ext_data])
        mock_ext_data_repo.get_last_ext_data_before_date = AsyncMock(return_value=ext_data)

        service = DashboardService(
            mock_events, mock_dashboard_repo, mock_ext_data_repo,
            mock_stations_repo, mock_stations_data_repo, mock_users_repo
        )
        result = await service.get_power_logs(PydanticObjectId(), start_date, end_date)
        assert result is not None
