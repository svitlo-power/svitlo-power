import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import aiohttp

from shared.services.outages_schedule.service import OutagesScheduleService
from shared.services.events.service import EventsService
from shared.repositories.interfaces.outages_schedule import IOutagesScheduleRepository
from shared.services.outages_schedule.models import SchedulesResponse, UnitSchedule, DaySchedule, Slot, SlotType, DayStatus


@pytest.fixture
def mock_events_service():
    return AsyncMock(spec=EventsService)


@pytest.fixture
def mock_aiohttp_session():
    return AsyncMock(spec=aiohttp.ClientSession)


@pytest.fixture
def mock_outages_repo():
    return AsyncMock(spec=IOutagesScheduleRepository)


@pytest.fixture
def outages_service(mock_events_service, mock_aiohttp_session, mock_outages_repo):
    return OutagesScheduleService(
        events=mock_events_service,
        session=mock_aiohttp_session,
        repository=mock_outages_repo,
    )


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


class TestOutagesScheduleService:
    @pytest.mark.asyncio
    async def test_get_schedule_async(self, outages_service, mock_outages_repo, sample_schedule):
        mock_outages_repo.get_schedule.return_value = sample_schedule
        
        result = await outages_service.get_schedule_async("queue_1")
        
        assert result is not None
        assert "queue_1" in result.root
        mock_outages_repo.get_schedule.assert_called_once_with("queue_1")

    @pytest.mark.asyncio
    async def test_get_schedule_async_not_found(self, outages_service, mock_outages_repo):
        mock_outages_repo.get_schedule.return_value = None
        
        result = await outages_service.get_schedule_async("queue_1")
        
        assert result is None
        mock_outages_repo.get_schedule.assert_called_once_with("queue_1")

    @pytest.mark.asyncio
    async def test_get_schedule_sync_not_running_loop(self, outages_service, mock_outages_repo, sample_schedule):
        mock_outages_repo.get_schedule.return_value = sample_schedule
        
        # Mock asyncio.get_event_loop to return a non-running loop
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = False
            mock_loop.run_until_complete.return_value = sample_schedule
            mock_get_loop.return_value = mock_loop
            
            result = outages_service.get_schedule("queue_1")
            
            assert result is not None
            assert "queue_1" in result.root

    @pytest.mark.asyncio
    async def test_get_schedule_sync_running_loop(self, outages_service):
        # Mock asyncio.get_event_loop to return a running loop
        with patch('asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop
            
            result = outages_service.get_schedule("queue_1")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_success(self, outages_service, mock_aiohttp_session, mock_outages_repo, mock_events_service):
        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "queue_1": {
                "today": {"date": "2024-01-15T00:00:00Z", "slots": [{"start": 0, "end": 24, "type": "Definite"}], "status": "ScheduleApplies"},
                "tomorrow": {"date": "2024-01-16T00:00:00Z", "slots": [{"start": 0, "end": 24, "type": "Definite"}], "status": "ScheduleApplies"},
                "updatedOn": "2024-01-15T10:00:00Z"
            }
        }
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
        
        # Mock repository set_schedule
        mock_outages_repo.set_schedule = AsyncMock()
        mock_outages_repo.get_all_schedules = AsyncMock(return_value=SchedulesResponse({}))
        
        result = await outages_service.update(region=1, dso=1)
        
        # First fetch: nothing stored before
        assert result.previous is None
        assert "queue_1" in result.current.root
        mock_aiohttp_session.get.assert_called_once()
        mock_outages_repo.set_schedule.assert_called_once()
        mock_events_service.broadcast_public.assert_called_once_with("outages_updated", None)

    @staticmethod
    def _yasno(slots, updated_on="2024-01-15T10:00:00Z", status="ScheduleApplies"):
        return {
            "queue_1": {
                # Today: days far from now are reset to WaitingForSchedule
                "today": {"date": datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00Z"), "slots": slots, "status": status},
                "updatedOn": updated_on,
            }
        }

    async def _update_twice(self, outages_service, mock_aiohttp_session, mock_outages_repo, first, second):
        stored = SchedulesResponse({})

        async def set_schedule(schedule):
            nonlocal stored
            stored = schedule

        mock_outages_repo.set_schedule = AsyncMock(side_effect=set_schedule)
        mock_outages_repo.get_all_schedules = AsyncMock(side_effect=lambda: stored)
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response

        mock_response.json.return_value = first
        await outages_service.update(region=1, dso=1)
        mock_response.json.return_value = second
        return await outages_service.update(region=1, dso=1)

    @pytest.mark.asyncio
    async def test_update_without_changes_does_not_broadcast(
        self, outages_service, mock_aiohttp_session, mock_outages_repo, mock_events_service,
    ):
        slots = [{"start": 480, "end": 720, "type": "Definite"}]
        result = await self._update_twice(
            outages_service, mock_aiohttp_session, mock_outages_repo,
            self._yasno(slots), self._yasno(slots, updated_on="2024-01-15T10:05:00Z"),
        )

        assert result.previous is not None
        assert result.changed is False
        # Only the first fetch broadcasts
        mock_events_service.broadcast_public.assert_called_once_with("outages_updated", None)

    @pytest.mark.asyncio
    async def test_update_with_changed_slots_broadcasts(
        self, outages_service, mock_aiohttp_session, mock_outages_repo, mock_events_service,
    ):
        result = await self._update_twice(
            outages_service, mock_aiohttp_session, mock_outages_repo,
            self._yasno([{"start": 480, "end": 720, "type": "Definite"}]),
            self._yasno([{"start": 600, "end": 720, "type": "Definite"}]),
        )

        assert result.changed is True
        assert result.previous.root["queue_1"].days[0].slots[0].start == 480
        assert result.current.root["queue_1"].days[0].slots[0].start == 600
        assert mock_events_service.broadcast_public.call_count == 2

    @pytest.mark.asyncio
    async def test_update_with_changed_status_broadcasts(
        self, outages_service, mock_aiohttp_session, mock_outages_repo, mock_events_service,
    ):
        result = await self._update_twice(
            outages_service, mock_aiohttp_session, mock_outages_repo,
            self._yasno([]), self._yasno([], status="EmergencyShutdowns"),
        )

        assert result.changed is True

    @pytest.mark.asyncio
    async def test_update_http_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_connection_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        import aiohttp
        mock_aiohttp_session.get.side_effect = aiohttp.ClientConnectionError("Connection failed")
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_timeout(self, outages_service, mock_aiohttp_session, mock_events_service):
        import asyncio
        mock_aiohttp_session.get.side_effect = asyncio.TimeoutError()
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_validation_error(self, outages_service, mock_aiohttp_session, mock_events_service):
        from pydantic import ValidationError
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"invalid": "data"}
        mock_aiohttp_session.get.return_value.__aenter__.return_value = mock_response
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_generic_exception(self, outages_service, mock_aiohttp_session, mock_events_service):
        mock_aiohttp_session.get.side_effect = Exception("Unexpected error")
        
        result = await outages_service.update(region=1, dso=1)
        
        assert result is None
        mock_events_service.broadcast_public.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])