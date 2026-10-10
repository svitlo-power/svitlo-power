"""Tests for shared/repositories/implementations/ext_data_read.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from beanie import PydanticObjectId

from shared.repositories.implementations.ext_data_read import ExtDataReadRepository
from shared.models.ext_data import ExtData


def make_comparison_mock():
    """Create a MagicMock that supports comparison operators with datetime."""
    m = MagicMock()
    m.__ge__ = lambda self, other: m
    m.__le__ = lambda self, other: m
    m.__lt__ = lambda self, other: m
    m.__gt__ = lambda self, other: m
    return m


# Mock Beanie class-level query attributes
ExtData.user_id = make_comparison_mock()
ExtData.received_at = make_comparison_mock()


class TestExtDataReadRepository:
    """Tests for ExtDataReadRepository."""

    @pytest.mark.asyncio
    async def test_get_last_ext_data_by_user_id(self):
        """Test get_last_ext_data_by_user_id."""
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_data = MagicMock(spec=ExtData)
        with patch.object(ExtData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=[mock_data])
            repo = ExtDataReadRepository()
            result = await repo.get_last_ext_data_by_user_id(user_id)
            assert result == mock_data
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_last_ext_data_by_user_id_empty(self):
        """Test get_last_ext_data_by_user_id when no data."""
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(ExtData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=[])
            repo = ExtDataReadRepository()
            result = await repo.get_last_ext_data_by_user_id(user_id)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_ext_data_statistics(self):
        """Test get_ext_data_statistics."""
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 1, 31)
        mock_data = [MagicMock(spec=ExtData)]
        with patch.object(ExtData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_data)
            repo = ExtDataReadRepository()
            result = await repo.get_ext_data_statistics(user_id, start_date, end_date)
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_last_ext_data_before_date(self):
        """Test get_last_ext_data_before_date."""
        user_id = 1
        before_date = datetime(2024, 1, 15)
        mock_data = MagicMock(spec=ExtData)
        with patch.object(ExtData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_data])
            repo = ExtDataReadRepository()
            result = await repo.get_last_ext_data_before_date(user_id, before_date)
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_last_ext_data_before_date_empty(self):
        """Test get_last_ext_data_before_date when no data."""
        user_id = 1
        before_date = datetime(2024, 1, 15)
        with patch.object(ExtData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
            repo = ExtDataReadRepository()
            result = await repo.get_last_ext_data_before_date(user_id, before_date)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_last_ext_data_before_date_exception(self):
        """Test get_last_ext_data_before_date handles exception."""
        user_id = 1
        before_date = datetime(2024, 1, 15)
        with patch.object(ExtData, 'find', side_effect=Exception("DB error")):
            repo = ExtDataReadRepository()
            result = await repo.get_last_ext_data_before_date(user_id, before_date)
            assert result is None