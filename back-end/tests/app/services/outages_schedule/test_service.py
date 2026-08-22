"""Tests for app/services/outages_schedule/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientConnectionError, ClientError
from pydantic import ValidationError
import asyncio

from app.services.outages_schedule.service import OutagesScheduleService
from app.services.outages_schedule.models import SchedulesResponse, DayStatus, SlotType, Slot, DaySchedule, UnitSchedule


class TestOutagesScheduleServiceInit:
    def test_init_with_session(self):
        mock_events = MagicMock()
        mock_session = MagicMock()
        service = OutagesScheduleService(mock_events, mock_session)
        assert service._session is mock_session
        assert service._cache.root == {}

    def test_init_without_session(self):
        mock_events = MagicMock()
        service = OutagesScheduleService(mock_events, session=None)
        assert service._session is None


class TestOutagesScheduleServiceGetSchedule:
    def test_get_schedule_returns_none_for_empty_cache(self):
        mock_events = MagicMock()
        mock_session = MagicMock()
        service = OutagesScheduleService(mock_events, mock_session)
        result = service.get_schedule("nonexistent")
        assert result is None

    def test_get_schedule_returns_cached_value(self):
        mock_events = MagicMock()
        mock_session = MagicMock()
        service = OutagesScheduleService(mock_events, mock_session)

        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot], date=now, status=DayStatus.ScheduleApplies)
        unit = UnitSchedule(days=[day], updatedOn=now)
        service._cache = SchedulesResponse.model_validate({"queue1": unit})

        result = service.get_schedule("queue1")
        assert result is not None
        assert len(result.days) == 1


class TestOutagesScheduleServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_success(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

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
        assert service._cache.root.get("queue1") is not None
        mock_events.broadcast_public.assert_called_once_with("outages_updated", None)

    @pytest.mark.asyncio
    async def test_update_non_200_status(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 500

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_connection_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ClientConnectionError("Connection failed"))

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_timeout(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_client_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=ClientError("Client error"))

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_validation_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"invalid": "data"})

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_sets_waiting_for_schedule_for_old_days(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

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
        assert service._cache.root["queue1"].days[0].status == DayStatus.WaitingForSchedule


class TestOutagesScheduleServiceUpdateExceptions:
    @pytest.mark.asyncio
    async def test_update_timeout_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=asyncio.TimeoutError())

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_client_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_session.get = MagicMock(side_effect=ClientError("Client error"))

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_validation_error(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"invalid": "data"})

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_generic_exception(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_session = MagicMock()

        service = OutagesScheduleService(mock_events, mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.status = 200
        mock_response.json = AsyncMock(side_effect=ValueError("Unexpected error"))

        mock_session.get = MagicMock(return_value=mock_response)

        result = await service.update(25, 902)
        assert result is None
        mock_events.broadcast_public.assert_not_called()
