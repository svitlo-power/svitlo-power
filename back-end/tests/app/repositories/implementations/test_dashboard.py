"""Tests for app/repositories/implementations/dashboard.py - write methods only.
Read methods are tested in shared/python/tests/repositories/test_dashboard_read.py
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.dashboard import DashboardRepository
from shared.models.building import Building

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
Building.order = MagicMock()
Building.station = MagicMock()
Building.station.id = MagicMock()


class TestDashboardRepository:
    """Tests for DashboardRepository write methods."""

    @pytest.mark.asyncio
    async def test_edit_building(self):
        """Test edit_building."""
        mock_building = MagicMock(spec=Building)
        mock_building.save = AsyncMock()
        
        repo = DashboardRepository()
        await repo.edit_building(mock_building)
        
        mock_building.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_building(self):
        """Test create_building."""
        mock_building = MagicMock(spec=Building)
        mock_building.id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_building.insert = AsyncMock()
        
        repo = DashboardRepository()
        result = await repo.create_building(mock_building)
        
        assert result == mock_building.id
        mock_building.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_building(self):
        """Test delete_building."""
        mock_building = MagicMock(spec=Building)
        mock_building.delete = AsyncMock()
        
        repo = DashboardRepository()
        await repo.delete_building(mock_building)
        
        mock_building.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reorder_buildings(self):
        """Test reorder_buildings."""
        b1 = MagicMock(spec=Building)
        b1.save = AsyncMock()
        b2 = MagicMock(spec=Building)
        b2.save = AsyncMock()
        
        repo = DashboardRepository()
        await repo.reorder_buildings([b1, b2])
        
        assert b1.order == 1
        assert b2.order == 2
        b1.save.assert_called_once()
        b2.save.assert_called_once()
