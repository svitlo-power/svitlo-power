"""Tests for shared/repositories/implementations/dashboard_read.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from shared.repositories.implementations.dashboard_read import DashboardReadRepository
from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig


# Mock Beanie class-level query attributes
Building.order = MagicMock()
Building.station = MagicMock()
Building.station.id = MagicMock()


class TestDashboardReadRepository:
    """Tests for DashboardReadRepository."""

    @pytest.mark.asyncio
    async def test_get_building(self):
        """Test get_building."""
        building_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_building = MagicMock(spec=Building)
        
        with patch.object(Building, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_building
            
            repo = DashboardReadRepository()
            result = await repo.get_building(building_id)
            
            assert result == mock_building
            mock_get.assert_called_once_with(building_id, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_building_by_station_id(self):
        """Test get_building_by_station_id."""
        station_id = 1
        mock_building = MagicMock(spec=Building)
        
        with patch.object(Building, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_building
            
            repo = DashboardReadRepository()
            result = await repo.get_building_by_station_id(station_id)
            
            assert result == mock_building
            mock_find_one.assert_called_once()
            call_args = mock_find_one.call_args
            assert call_args[1]['fetch_links'] is True

    @pytest.mark.asyncio
    async def test_get_buildings_all(self):
        """Test get_buildings with all=True."""
        mock_buildings = [MagicMock(spec=Building)]
        with patch.object(Building, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_buildings)
            repo = DashboardReadRepository()
            result = await repo.get_buildings(all=True)
            assert result == mock_buildings
            mock_find.assert_called_once_with({}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_buildings_enabled_only(self):
        """Test get_buildings with all=False (enabled only)."""
        mock_buildings = [MagicMock(spec=Building)]
        with patch.object(Building, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_buildings)
            repo = DashboardReadRepository()
            result = await repo.get_buildings(all=False)
            assert result == mock_buildings
            mock_find.assert_called_once_with({"enabled": True}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_buildings_with_ids(self):
        """Test get_buildings with specific ids."""
        mock_buildings = [MagicMock(spec=Building)]
        ids = [PydanticObjectId("507f1f77bcf86cd799439011")]
        with patch.object(Building, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_buildings)
            repo = DashboardReadRepository()
            result = await repo.get_buildings(ids=ids)
            assert result == mock_buildings
            mock_find.assert_called_once_with({"_id": {"$in": ids}}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_config(self):
        """Test get_config."""
        mock_config = MagicMock(spec=DashboardConfig)
        with patch.object(DashboardConfig, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_config
            repo = DashboardReadRepository()
            result = await repo.get_config()
            assert result == mock_config