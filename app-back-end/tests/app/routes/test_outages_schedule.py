"""Tests for outages schedule routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from shared.services.outages_schedule.service import OutagesScheduleService
from shared.services.outages_schedule.models import SchedulesResponse, UnitSchedule, DaySchedule, Slot, SlotType, DayStatus


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.DEBUG = True
    settings.APP_ACCESS_TOKEN = None
    return settings


@pytest.fixture
def mock_outages_service():
    return AsyncMock(spec=OutagesScheduleService)


@pytest.fixture
def app(mock_settings, mock_outages_service):
    """Create test app with mocked dependencies."""
    from fastapi_injector import InjectorMiddleware, attach_injector
    from injector import Injector, Module, provider
    from app.container import AppModule
    
    # Create a test module that provides our mocked service
    class TestModule(Module):
        @provider
        def provide_outages_schedule_service(self) -> OutagesScheduleService:
            return mock_outages_service
    
    injector = Injector([AppModule(), TestModule()])
    app = create_app(mock_settings)
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def sample_schedule():
    return SchedulesResponse(
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


class TestOutagesScheduleRoutes:
    @pytest.mark.asyncio
    async def test_get_outages_schedule_success(self, client, mock_outages_service, sample_schedule):
        mock_outages_service.get_schedule_async.return_value = sample_schedule
        
        response = client.get("/api/outagesSchedule/outagesSchedule/queue_1")
        
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert len(data["days"]) == 1
        assert data["days"][0]["status"] == "ScheduleApplies"

    @pytest.mark.asyncio
    async def test_get_outages_schedule_not_found(self, client, mock_outages_service):
        mock_outages_service.get_schedule_async.return_value = None
        
        response = client.get("/api/outagesSchedule/outagesSchedule/queue_1")
        
        assert response.status_code == 404
        assert "No schedule found for queue" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_outages_schedule_queue_not_in_response(self, client, mock_outages_service, sample_schedule):
        # Schedule exists but not for the requested queue
        mock_outages_service.get_schedule_async.return_value = sample_schedule
        
        response = client.get("/api/outagesSchedule/outagesSchedule/queue_2")
        
        assert response.status_code == 404
        assert "No schedule found for queue" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])