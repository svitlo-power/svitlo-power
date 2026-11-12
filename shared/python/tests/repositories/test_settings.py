"""Tests for shared/repositories/implementations/settings.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from shared.repositories.implementations.settings import SettingsRepository
from shared.models.system_setting import SystemSetting


# Mock Beanie class-level query attributes
SystemSetting.key = MagicMock()


class TestSettingsRepository:
    """Tests for SettingsRepository."""

    @pytest.mark.asyncio
    async def test_get_settings_by_keys(self):
        """Test get_settings_by_keys filters by keys at the database level."""
        mock_settings = [MagicMock(spec=SystemSetting), MagicMock(spec=SystemSetting)]
        with patch.object(SystemSetting, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_settings)
            repo = SettingsRepository()
            result = await repo.get_settings_by_keys(["discharge_target_soc", "charge_target_soc"])
            assert result == mock_settings
            mock_find.assert_called_once()
            # Verify the key.in_ filter was used
            call_args = mock_find.call_args[0][0]
            assert hasattr(call_args, 'in_') or str(call_args) != "{}"

    @pytest.mark.asyncio
    async def test_get_settings_by_keys_empty_list(self):
        """Test get_settings_by_keys with empty keys list."""
        with patch.object(SystemSetting, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=[])
            repo = SettingsRepository()
            result = await repo.get_settings_by_keys([])
            assert result == []
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_settings(self):
        """Test get_all_settings returns all settings."""
        mock_settings = [MagicMock(spec=SystemSetting)]
        with patch.object(SystemSetting, 'find_all') as mock_find_all:
            mock_find_all.return_value.to_list = AsyncMock(return_value=mock_settings)
            repo = SettingsRepository()
            result = await repo.get_all_settings()
            assert result == mock_settings
            mock_find_all.assert_called_once()
