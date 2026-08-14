"""Tests for app/services/visit_counter/service.py."""
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.visit_counter.service import VisitCounterService


class TestVisitCounterService:
    @pytest.mark.asyncio
    async def test_add_visit_total(self):
        mock_repo = MagicMock()
        mock_repo.increase_total_visits_counter = AsyncMock()
        mock_repo.increase_daily_visits_counter = AsyncMock()
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()

        service = VisitCounterService(mock_events, mock_repo)
        await service.add_visit("total", None)

        mock_repo.increase_total_visits_counter.assert_called_once()
        mock_repo.increase_daily_visits_counter.assert_not_called()
        mock_events.broadcast_public.assert_called_once_with("visits_updated", None)

    @pytest.mark.asyncio
    async def test_add_visit_daily(self):
        mock_repo = MagicMock()
        mock_repo.increase_total_visits_counter = AsyncMock()
        mock_repo.increase_daily_visits_counter = AsyncMock()
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()

        service = VisitCounterService(mock_events, mock_repo)
        await service.add_visit("daily", "2024-01-15")

        mock_repo.increase_total_visits_counter.assert_not_called()
        mock_repo.increase_daily_visits_counter.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("visits_updated", None)

    @pytest.mark.asyncio
    async def test_add_visit_daily_with_none_date(self):
        mock_repo = MagicMock()
        mock_repo.increase_total_visits_counter = AsyncMock()
        mock_repo.increase_daily_visits_counter = AsyncMock()
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()

        service = VisitCounterService(mock_events, mock_repo)
        await service.add_visit("daily", None)

        mock_repo.increase_daily_visits_counter.assert_called_once()
        called_date = mock_repo.increase_daily_visits_counter.call_args[0][0]
        assert called_date == date.today()

    @pytest.mark.asyncio
    async def test_add_visit_daily_with_invalid_date(self):
        mock_repo = MagicMock()
        mock_repo.increase_total_visits_counter = AsyncMock()
        mock_repo.increase_daily_visits_counter = AsyncMock()
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()

        service = VisitCounterService(mock_events, mock_repo)
        await service.add_visit("daily", "invalid-date")

        mock_repo.increase_daily_visits_counter.assert_called_once()
        called_date = mock_repo.increase_daily_visits_counter.call_args[0][0]
        assert called_date == date.today()

    @pytest.mark.asyncio
    async def test_add_visit_unknown_type(self):
        mock_repo = MagicMock()
        mock_repo.increase_total_visits_counter = AsyncMock()
        mock_repo.increase_daily_visits_counter = AsyncMock()
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()

        service = VisitCounterService(mock_events, mock_repo)
        await service.add_visit("unknown", None)

        mock_repo.increase_total_visits_counter.assert_not_called()
        mock_repo.increase_daily_visits_counter.assert_not_called()
        mock_events.broadcast_public.assert_called_once_with("visits_updated", None)

    @pytest.mark.asyncio
    async def test_get_today_stats(self):
        mock_repo = MagicMock()
        mock_repo.get_today_stats = AsyncMock(return_value=(100, 50))
        mock_events = MagicMock()

        service = VisitCounterService(mock_events, mock_repo)
        result = await service.get_today_stats()

        assert result == {"totalVisitors": 100, "dailyVisitors": 50}
