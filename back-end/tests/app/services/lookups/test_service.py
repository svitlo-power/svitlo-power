"""Tests for app/services/lookups/service.py."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from beanie import PydanticObjectId

from app.services.lookups.service import LookupsService
from shared.models.lookup import LookupValue


class TestLookupsService:
    @pytest.mark.asyncio
    async def test_get_lookup_values_delegates_to_repository(self):
        mock_repo = MagicMock()
        mock_repo.get_lookup_values = AsyncMock(return_value=[LookupValue(value=PydanticObjectId(), text="Test")])

        service = LookupsService(mock_repo)
        result = await service.get_lookup_values("test_schema")

        mock_repo.get_lookup_values.assert_called_once_with("test_schema")
        assert len(result) == 1
        assert result[0].text == "Test"

    @pytest.mark.asyncio
    async def test_get_lookup_values_empty_result(self):
        mock_repo = MagicMock()
        mock_repo.get_lookup_values = AsyncMock(return_value=[])

        service = LookupsService(mock_repo)
        result = await service.get_lookup_values("empty_schema")

        assert result == []
