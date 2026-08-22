"""Tests for app/repositories/implementations/visits_counter.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, date

from app.repositories.implementations.visits_counter import VisitsCounterRepository
from shared.models.visit_counter import DailyVisitCounter, VisitCounter

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
DailyVisitCounter.date = MagicMock()


class TestVisitsCounterRepository:
    """Tests for VisitsCounterRepository."""

    @pytest.mark.asyncio
    async def test_increase_total_visits_counter_new(self):
        """Test increase_total_visits_counter when no counter exists yet."""
        with patch.object(VisitCounter, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            with patch.object(VisitCounter, 'insert', new_callable=AsyncMock) as mock_insert:
                with patch.object(VisitCounter, 'save', new_callable=AsyncMock) as mock_save:
                    repo = VisitsCounterRepository()
                    await repo.increase_total_visits_counter()
                    
                    mock_insert.assert_called_once()
                    mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_increase_total_visits_counter_existing(self):
        """Test increase_total_visits_counter when counter already exists."""
        mock_counter = MagicMock(spec=VisitCounter)
        mock_counter.visits_count = 10
        mock_counter.save = AsyncMock()
        
        with patch.object(VisitCounter, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_counter
            
            repo = VisitsCounterRepository()
            await repo.increase_total_visits_counter()
            
            assert mock_counter.visits_count == 11
            mock_counter.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_increase_daily_visits_counter_new(self):
        """Test increase_daily_visits_counter when no daily counter exists yet."""
        visit_date = datetime.now()
        with patch.object(DailyVisitCounter, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            with patch.object(DailyVisitCounter, 'insert', new_callable=AsyncMock) as mock_insert:
                with patch.object(DailyVisitCounter, 'save', new_callable=AsyncMock) as mock_save:
                    repo = VisitsCounterRepository()
                    await repo.increase_daily_visits_counter(visit_date)
                    
                    mock_insert.assert_called_once()
                    mock_save.assert_called_once()

    @pytest.mark.asyncio
    async def test_increase_daily_visits_counter_existing(self):
        """Test increase_daily_visits_counter when daily counter already exists."""
        visit_date = datetime.now()
        mock_counter = MagicMock(spec=DailyVisitCounter)
        mock_counter.visits_count = 5
        mock_counter.save = AsyncMock()
        
        with patch.object(DailyVisitCounter, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_counter
            
            repo = VisitsCounterRepository()
            await repo.increase_daily_visits_counter(visit_date)
            
            assert mock_counter.visits_count == 6
            mock_counter.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_today_stats(self):
        """Test get_today_stats."""
        mock_total = MagicMock(spec=VisitCounter)
        mock_total.visits_count = 100
        mock_daily = MagicMock(spec=DailyVisitCounter)
        mock_daily.visits_count = 20
        
        with patch.object(VisitCounter, 'find_one', new_callable=AsyncMock) as mock_find_total:
            mock_find_total.return_value = mock_total
            with patch.object(DailyVisitCounter, 'find_one', new_callable=AsyncMock) as mock_find_daily:
                mock_find_daily.return_value = mock_daily
                
                repo = VisitsCounterRepository()
                total, today = await repo.get_today_stats()
                
                assert total == 100
                assert today == 20

    @pytest.mark.asyncio
    async def test_get_today_stats_none(self):
        """Test get_today_stats when no counter exists yet."""
        with patch.object(VisitCounter, 'find_one', new_callable=AsyncMock) as mock_find_total:
            mock_find_total.return_value = None
            with patch.object(DailyVisitCounter, 'find_one', new_callable=AsyncMock) as mock_find_daily:
                mock_find_daily.return_value = None
                
                repo = VisitsCounterRepository()
                total, today = await repo.get_today_stats()
                
                assert total == 0
                assert today == 0
