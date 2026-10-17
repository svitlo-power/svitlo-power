"""Tests for app/repositories/implementations/ext_data.py - back-end specific methods only.
Read methods (get_last_ext_data_by_user_id, get_ext_data_statistics, get_last_ext_data_before_date)
are tested in shared/python/tests/repositories/test_ext_data_read.py
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from beanie import PydanticObjectId

from app.repositories.implementations.ext_data import ExtDataRepository
from shared.models.ext_data import ExtData
from app.models.sorting_config import SortingConfig


def make_comparison_mock():
    """Create a MagicMock that supports comparison operators with datetime."""
    m = MagicMock()
    m.__ge__ = lambda self, other: m
    m.__le__ = lambda self, other: m
    m.__lt__ = lambda self, other: m
    m.__gt__ = lambda self, other: m
    return m


# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
ExtData.user_id = make_comparison_mock()
ExtData.received_at = make_comparison_mock()


class TestExtDataRepository:
    """Tests for ExtDataRepository back-end specific methods."""

    def test_build_reference_joins_user_id(self):
        """Test build_reference_joins with user_id sorting."""
        repo = ExtDataRepository()
        sorting = SortingConfig(column="user_id", order="asc")
        joins = repo.build_reference_joins(sorting)
        assert len(joins) == 2
        assert joins[0]["$lookup"]["from"] == "users"

    def test_build_reference_joins_other(self):
        """Test build_reference_joins with other sorting."""
        repo = ExtDataRepository()
        sorting = SortingConfig(column="received_at", order="asc")
        joins = repo.build_reference_joins(sorting)
        assert joins == []

    def test_build_sort_stage_user_id(self):
        """Test build_sort_stage with user_id."""
        repo = ExtDataRepository()
        sorting = SortingConfig(column="user_id", order="asc")
        sort_stage = repo.build_sort_stage(sorting)
        assert sort_stage == {"user.name": 1}

    def test_build_sort_stage_other(self):
        """Test build_sort_stage with other fields."""
        repo = ExtDataRepository()
        sorting = SortingConfig(column="received_at", order="desc")
        sort_stage = repo.build_sort_stage(sorting)
        assert sort_stage == {"received_at": -1}

    def test_build_sort_stage_none(self):
        """Test build_sort_stage with None."""
        repo = ExtDataRepository()
        sort_stage = repo.build_sort_stage(None)
        assert sort_stage == {}

    @pytest.mark.asyncio
    async def test_get_ext_data(self):
        """Test get_ext_data."""
        repo = ExtDataRepository()
        with patch.object(repo, 'get_data', new_callable=AsyncMock) as mock_get_data:
            mock_get_data.return_value = ([], 0)
            result = await repo.get_ext_data(None)
            assert result == ([], 0)
            mock_get_data.assert_called_once_with(None)

    @pytest.mark.asyncio
    async def test_get_ext_data_by_id(self):
        """Test get_ext_data_by_id."""
        ext_data_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_data = MagicMock(spec=ExtData)
        with patch.object(ExtData, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_data
            repo = ExtDataRepository()
            result = await repo.get_ext_data_by_id(ext_data_id)
            assert result == mock_data
            mock_get.assert_called_once_with(ext_data_id)

    @pytest.mark.asyncio
    async def test_add_ext_data(self):
        """Test add_ext_data."""
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        grid_state = True
        dt = datetime.now(timezone.utc)
        
        with patch('app.repositories.implementations.ext_data.ExtData') as mock_ext_data_class:
            mock_instance = MagicMock()
            mock_instance.id = PydanticObjectId("507f1f77bcf86cd799439012")
            mock_instance.insert = AsyncMock()
            mock_ext_data_class.return_value = mock_instance
            
            repo = ExtDataRepository()
            result = await repo.add_ext_data(user_id, grid_state, dt)
            
            assert result == mock_instance.id
            mock_instance.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_found(self):
        """Test delete when exists."""
        ext_data_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_data = MagicMock(spec=ExtData)
        mock_data.delete = AsyncMock()
        with patch.object(ExtData, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_data
            repo = ExtDataRepository()
            result = await repo.delete(ext_data_id)
            assert result is True
            mock_data.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self):
        """Test delete when not found."""
        ext_data_id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(ExtData, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            repo = ExtDataRepository()
            result = await repo.delete(ext_data_id)
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_old_data(self):
        """Test delete_old_data."""
        with patch.object(ExtData, 'received_at', make_comparison_mock()), \
             patch.object(ExtData, 'find') as mock_find:
            mock_find.return_value.delete = AsyncMock()
            repo = ExtDataRepository()
            await repo.delete_old_data(5)
            mock_find.assert_called_once()
            mock_find.return_value.delete.assert_called_once()
