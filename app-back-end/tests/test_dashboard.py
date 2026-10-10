import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from beanie import PydanticObjectId

from shared.models import (
    Building,
    DashboardConfig,
    ExtData,
    Station,
    StationData,
    User,
)
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    DashboardConfigResponse,
    EditBuildingResponse,
    PowerLogsResponse,
    PeriodResponse,
)
from shared.models.api.dashboard import PowerLogsRequest, BuildingsSummaryRequest
from shared.services.dashboard import ReadOnlyDashboardService
from shared.services.outages_schedule import OutagesScheduleService
from shared.services.events import EventsService
from shared.repositories.interfaces import (
    IDashboardReadRepository,
    IExtDataReadRepository,
    IStationsReadRepository,
    IStationsDataReadRepository,
    IUsersReadRepository,
    IOutagesScheduleRepository,
)
from shared.services.outages_schedule.models import SchedulesResponse, UnitSchedule, DaySchedule, Slot, SlotType, DayStatus


@pytest.fixture
def mock_dashboard_repo():
    return AsyncMock(spec=IDashboardReadRepository)


@pytest.fixture
def mock_ext_data_repo():
    return AsyncMock(spec=IExtDataReadRepository)


@pytest.fixture
def mock_stations_repo():
    return AsyncMock(spec=IStationsReadRepository)


@pytest.fixture
def mock_stations_data_repo():
    return AsyncMock(spec=IStationsDataReadRepository)


@pytest.fixture
def mock_users_repo():
    return AsyncMock(spec=IUsersReadRepository)


@pytest.fixture
def mock_events_service():
    return AsyncMock(spec=EventsService)


@pytest.fixture
def mock_outages_repo():
    return AsyncMock(spec=IOutagesScheduleRepository)


@pytest.fixture
def mock_aiohttp_session():
    return AsyncMock()


@pytest.fixture
def dashboard_service(
    mock_events_service,
    mock_dashboard_repo,
    mock_ext_data_repo,
    mock_stations_repo,
    mock_stations_data_repo,
    mock_users_repo,
):
    return ReadOnlyDashboardService(
        events=mock_events_service,
        dashboard=mock_dashboard_repo,
        ext_data=mock_ext_data_repo,
        stations=mock_stations_repo,
        stations_data=mock_stations_data_repo,
        users=mock_users_repo,
    )


@pytest.fixture
def outages_service(mock_events_service, mock_aiohttp_session, mock_outages_repo):
    return OutagesScheduleService(
        events=mock_events_service,
        session=mock_aiohttp_session,
        repository=mock_outages_repo,
    )


@pytest.fixture
def sample_building():
    station = MagicMock()
    station.id = PydanticObjectId()
    station.station_name = "Test Station"
    station.battery_capacity = 10000
    station.connection_status = "ONLINE"
    
    user = MagicMock()
    user.id = PydanticObjectId()
    user.name = "Test User"
    user.email = "test@example.com"
    
    building = MagicMock()
    building.id = PydanticObjectId()
    building.name = {"en": "Test Building"}
    building.color = "#FF0000"
    building.station = station
    building.report_users = [user]
    building.enabled = True
    building.order = 1
    return building


@pytest.fixture
def sample_dashboard_config():
    config = MagicMock()
    config.title = {"en": "Test Dashboard"}
    config.enable_outages_schedule = True
    config.outages_schedule_queue = "queue_1"
    return config


@pytest.fixture
def sample_ext_data():
    ext_data = MagicMock()
    ext_data.user_id = PydanticObjectId()
    ext_data.grid_state = True
    ext_data.received_at = datetime.now(timezone.utc)
    return ext_data


@pytest.fixture
def sample_station_data():
    station_data = MagicMock()
    station_data.station_id = 12345
    station_data.battery_soc = 85
    station_data.charge_power = -2000
    station_data.discharge_power = 0
    station_data.generation_power = 0
    station_data.wire_power = 0
    station_data.consumption_power = 1500
    station_data.last_update_time = datetime.now(timezone.utc)
    return station_data


class TestReadOnlyDashboardService:
    @pytest.mark.asyncio
    async def test_get_config(self, dashboard_service, mock_dashboard_repo, sample_dashboard_config):
        mock_dashboard_repo.get_config.return_value = sample_dashboard_config
        
        result = await dashboard_service.get_config()
        
        assert isinstance(result, DashboardConfigResponse)
        assert result.title.get_culture_value("en") == "Test Dashboard"
        assert result.enable_outages_schedule is True
        assert result.outages_schedule_queue == "queue_1"

    @pytest.mark.asyncio
    async def test_get_buildings(self, dashboard_service, mock_dashboard_repo, sample_building):
        mock_dashboard_repo.get_buildings.return_value = [sample_building]
        
        result = await dashboard_service.get_buildings(all=False)
        
        assert len(result) == 1
        assert isinstance(result[0], BuildingResponse)
        assert result[0].name.get_culture_value("en") == "Test Building"
        assert result[0].color == "#FF0000"
        assert result[0].has_bound_station is True

    @pytest.mark.asyncio
    async def test_get_building(self, dashboard_service, mock_dashboard_repo, sample_building):
        mock_dashboard_repo.get_building.return_value = sample_building
        
        result = await dashboard_service.get_building(sample_building.id)
        
        assert isinstance(result, EditBuildingResponse)
        assert result.name.get_culture_value("en") == "Test Building"
        assert result.station_id == sample_building.station.id
        assert result.enabled is True

    @pytest.mark.asyncio
    async def test_get_building_not_found(self, dashboard_service, mock_dashboard_repo):
        mock_dashboard_repo.get_building.return_value = None
        
        result = await dashboard_service.get_building(PydanticObjectId())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_buildings_summary(
        self, 
        dashboard_service, 
        mock_dashboard_repo, 
        mock_ext_data_repo,
        mock_stations_data_repo,
        sample_building,
        sample_ext_data,
        sample_station_data,
    ):
        mock_dashboard_repo.get_buildings.return_value = [sample_building]
        mock_ext_data_repo.get_last_ext_data_by_user_id.return_value = sample_ext_data
        mock_stations_data_repo.get_last_station_data.return_value = sample_station_data
        mock_stations_data_repo.get_assumed_connection_status.return_value = "ONLINE"
        mock_stations_data_repo.get_station_data_average_column.return_value = 1500
        
        result = await dashboard_service.get_buildings_summary([sample_building.id])
        
        assert len(result) == 1
        assert isinstance(result[0], BuildingSummaryResponse)
        assert result[0].id == sample_building.id
        assert result[0].is_grid_available is True
        assert result[0].battery_percent == 85

    @pytest.mark.asyncio
    async def test_get_buildings_with_summary(
        self,
        dashboard_service,
        mock_dashboard_repo,
        mock_ext_data_repo,
        mock_stations_data_repo,
        sample_building,
        sample_ext_data,
        sample_station_data,
    ):
        mock_dashboard_repo.get_buildings.return_value = [sample_building]
        mock_ext_data_repo.get_last_ext_data_by_user_id.return_value = sample_ext_data
        mock_stations_data_repo.get_last_station_data.return_value = sample_station_data
        mock_stations_data_repo.get_assumed_connection_status.return_value = "ONLINE"
        mock_stations_data_repo.get_station_data_average_column.return_value = 1500
        
        result = await dashboard_service.get_buildings_with_summary()
        
        assert len(result) == 1
        assert isinstance(result[0], BuildingWithSummaryResponse)
        assert result[0].name.get_culture_value("en") == "Test Building"
        assert result[0].battery_percent == 85


class TestOutagesScheduleService:
    @pytest.mark.asyncio
    async def test_get_schedule_async(self, outages_service, mock_outages_repo):
        schedule = SchedulesResponse(
            root={
                "queue_1": UnitSchedule(
                    days=[
                        DaySchedule(
                            slots=[Slot(start=0, end=24, type=SlotType.Definite)],
                            date=datetime.now(timezone.utc),
                            status=DayStatus.ScheduleApplies,
                        ),
                    ],
                    updatedOn=datetime.now(timezone.utc),
                )
            }
        )
        mock_outages_repo.get_schedule.return_value = schedule
        
        result = await outages_service.get_schedule_async("queue_1")
        
        assert result is not None
        assert "queue_1" in result.root

    @pytest.mark.asyncio
    async def test_get_schedule_async_not_found(self, outages_service, mock_outages_repo):
        mock_outages_repo.get_schedule.return_value = None
        
        result = await outages_service.get_schedule_async("queue_1")
        
        assert result is None


class TestRoutes:
    @pytest.mark.asyncio
    async def test_get_buildings_route(self):
        # This would require a full integration test setup
        # For now, we test the service layer directly
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])