"""Tests for app/repositories/implementations/dashboard.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.dashboard import DashboardRepository
from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
Building.order = MagicMock()


class TestDashboardRepository:
    """Tests for DashboardRepository."""

    @pytest.mark.asyncio
    async def test_get_building(self):
        """Test get_building."""
        building_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_building = MagicMock(spec=Building)
        
        with patch.object(Building, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_building
            
            repo = DashboardRepository()
            result = await repo.get_building(building_id)
            
            assert result == mock_building
            mock_get.assert_called_once_with(building_id, fetch_links=True)

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

    @pytest.mark.asyncio
    async def test_get_buildings_by_ids(self):
        """Test get_buildings with ids parameter."""
        ids = [PydanticObjectId("507f1f77bcf86cd799439011")]
        mock_buildings = [MagicMock(spec=Building)]
        
        with patch.object(Building, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_buildings)
            
            repo = DashboardRepository()
            result = await repo.get_buildings(ids=ids)
            
            assert result == mock_buildings
            mock_find.assert_called_once_with({"_id": {"$in": ids}}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_buildings_enabled_only(self):
        """Test get_buildings enabled only."""
        mock_buildings = [MagicMock(spec=Building)]
        
        with patch.object(Building, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_buildings)
            
            repo = DashboardRepository()
            result = await repo.get_buildings(all=False)
            
            assert result == mock_buildings
            mock_find.assert_called_once_with({"enabled": True}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_buildings_all(self):
        """Test get_buildings all."""
        mock_buildings = [MagicMock(spec=Building)]
        
        with patch.object(Building, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_buildings)
            
            repo = DashboardRepository()
            result = await repo.get_buildings(all=True)
            
            assert result == mock_buildings
            mock_find.assert_called_once_with({}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_config(self):
        """Test get_config."""
        mock_config = MagicMock(spec=DashboardConfig)
        
        with patch.object(DashboardConfig, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_config
            
            repo = DashboardRepository()
            result = await repo.get_config()
            
            assert result == mock_config
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_config_existing(self):
        """Test save_config when config exists."""
        config_data = MagicMock(spec=DashboardConfig)
        config_data.title = {"en": "New Title"}
        config_data.enable_outages_schedule = True
        config_data.outages_schedule_queue = "queue"
        mock_existing = MagicMock(spec=DashboardConfig)
        mock_existing.save = AsyncMock()
        
        with patch.object(DashboardConfig, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_existing
            
            repo = DashboardRepository()
            await repo.save_config(config_data)
            
            assert mock_existing.title == {"en": "New Title"}
            assert mock_existing.enable_outages_schedule is True
            assert mock_existing.outages_schedule_queue == "queue"
            mock_existing.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_config_new(self):
        """Test save_config when no config exists."""
        config_data = MagicMock(spec=DashboardConfig)
        config_data.insert = AsyncMock()
        
        with patch.object(DashboardConfig, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            
            repo = DashboardRepository()
            await repo.save_config(config_data)
            
            config_data.insert.assert_called_once()
