"""Tests for shared/services/outages_schedule/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientConnectionError, ClientError
from pydantic import ValidationError
import asyncio

from shared.services.outages_schedule.service import OutagesScheduleService
from shared.services.outages_schedule.models import SchedulesResponse, DayStatus, SlotType, Slot, DaySchedule, UnitSchedule
from shared.repositories.interfaces.outages_schedule import IOutagesScheduleRepository


class TestOutagesScheduleServiceInit:
    def test_init_with_session_and_repository(self):
        mock_events = MagicMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)
        service = OutagesScheduleService(mock_events, mock_session, mock_repo)
        assert service._session is mock_session
        assert service._repository is mock_repo


class TestOutagesScheduleServiceGetSchedule:
    def test_get_schedule_returns_none_for_empty_cache(self):
        mock_events = MagicMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)
        mock_repo.get_schedule = AsyncMock(return_value=None)
        service = OutagesScheduleService(mock_events, mock_session, mock_repo)
        result = service.get_schedule("nonexistent")
        assert result is None

    def test_get_schedule_returns_cached_value(self):
        mock_events = MagicMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)
        
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot], date=now, status=DayStatus.ScheduleApplies)
        unit = UnitSchedule(days=[day], updatedOn=now)
        schedule = SchedulesResponse.model_validate({"queue1": unit})
        mock_repo.get_schedule = AsyncMock(return_value=schedule)
        
        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        result = service.get_schedule("queue1")
        assert result is not None
        # get_schedule returns SchedulesResponse with the queue's data
        assert "queue1" in result.root
        assert len(result.root["queue1"].days) == 1


class TestOutagesScheduleServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_success(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)
        mock_repo.set_schedule = AsyncMock()

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "queue1": {
                "today": {"slots": [{"start": 0, "end": 120, "type": "Definite"}], "date": "2024-01-01T00:00:00Z", "status": "ScheduleApplies"},
                "tomorrow": {"slots": [{"start": 0, "end": 120, "type": "Definite"}], "date": "2024-01-02T00:00:00Z", "status": "ScheduleApplies"},
                "updatedOn": "2024-01-01T00:00:00Z",
            }
        })

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None  # update returns None on success
        mock_repo.set_schedule.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("outages_updated", None)

    @pytest.mark.asyncio
    async def test_update_non_200_status(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 500

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_connection_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ClientConnectionError("Connection failed"))

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_timeout(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_client_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=ClientError("Client error"))

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_validation_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"invalid": "data"})

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_sets_waiting_for_schedule_for_old_days(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)
        mock_repo.set_schedule = AsyncMock()

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        old_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "queue1": {
                "today": {"slots": [{"start": 0, "end": 120, "type": "Definite"}], "date": old_date, "status": "ScheduleApplies"},
                "updatedOn": "2024-01-01T00:00:00Z",
            }
        })

        mock_session.get = MagicMock(return_value=mock_response)

        await service.update(25, 902)
        # Verify the schedule was set with WaitingForSchedule status
        mock_repo.set_schedule.assert_called_once()
        call_args = mock_repo.set_schedule.call_args[0][0]
        assert call_args.root["queue1"].days[0].status == DayStatus.WaitingForSchedule


class TestOutagesScheduleServiceUpdateExceptions:
    @pytest.mark.asyncio
    async def test_update_timeout_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_client_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=ClientError("Client error"))

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_validation_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"invalid": "data"})

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_generic_exception(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()
        mock_repo = MagicMock(spec=IOutagesScheduleRepository)

        service = OutagesScheduleService(mock_events, mock_session, mock_repo)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
        mock_repo.set_schedule.assert_not_called()