"""Tests for app/repositories/implementations/test_lookups.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.lookups import LookupsRepository
from shared.models.lookup import LookupValue
from shared.models import Building, User


class TestLookupsRepository:
    """Tests for LookupsRepository."""

    @pytest.mark.asyncio
    async def test_get_lookup_values(self):
        """Test get_lookup_values."""
        mock_values = [LookupValue(value=PydanticObjectId("507f1f77bcf86cd799439011"), text="Building 1")]
        
        # Patch Building.get_lookup_values to return mock_values
        with patch.object(Building, 'get_lookup_values', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_values
            
            repo = LookupsRepository()
            result = await repo.get_lookup_values("building")
            
            assert result == mock_values
            mock_get.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_lookup_values_with_filters(self):
        """Test get_lookup_values with reporter_user containing filters."""
        mock_values = [LookupValue(value=PydanticObjectId("507f1f77bcf86cd799439012"), text="User 1")]
        
        with patch.object(User, 'get_lookup_values', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_values
            
            repo = LookupsRepository()
            result = await repo.get_lookup_values("reporter_user")
            
            assert result == mock_values
            mock_get.assert_called_once_with({"is_reporter": True})

    def test_is_lookup_model(self):
        """Test _is_lookup_model TypeGuard."""
        assert LookupsRepository._is_lookup_model(Building) is True
        
        class NonLookup:
            pass
            
        assert LookupsRepository._is_lookup_model(NonLookup) is False
