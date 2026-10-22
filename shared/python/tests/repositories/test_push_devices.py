"""Tests for shared/repositories/implementations/push_devices.py."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.models.push_device import PushDevice
from shared.repositories.implementations.push_devices import PushDevicesRepository, _DeviceToken, _DeviceRecipient
from shared.repositories.interfaces.push_devices import PushRecipient


def _find_returning(tokens):
    find = MagicMock()
    find.return_value.project.return_value.to_list = AsyncMock(
        return_value=[_DeviceToken(token=t) for t in tokens]
    )
    return find


class TestPushDevicesRepositoryTokens:
    @pytest.mark.asyncio
    async def test_get_topic_tokens_projects_only_tokens(self):
        find = _find_returning(["a", "b"])
        with patch.object(PushDevice, "find", find):
            result = await PushDevicesRepository().get_topic_tokens("schedule_changes")

        assert result == ["a", "b"]
        find.assert_called_once_with({"enabled": True, "disabled_topics": {"$ne": "schedule_changes"}})
        find.return_value.project.assert_called_once_with(_DeviceToken)

    @pytest.mark.asyncio
    async def test_get_topic_recipients_returns_token_and_language(self):
        find = MagicMock()
        find.return_value.project.return_value.to_list = AsyncMock(return_value=[
            _DeviceRecipient(token="a", language="en"),
            _DeviceRecipient(token="b", language="uk"),
        ])
        with patch.object(PushDevice, "find", find):
            result = await PushDevicesRepository().get_topic_recipients("power_status")

        assert result == [PushRecipient("a", "en"), PushRecipient("b", "uk")]
        # Same opt-out filter as the token query, no building filter
        find.assert_called_once_with({"enabled": True, "disabled_topics": {"$ne": "power_status"}})
        find.return_value.project.assert_called_once_with(_DeviceRecipient)

    @pytest.mark.asyncio
    async def test_get_enabled_tokens_projects_only_tokens(self):
        find = _find_returning(["a"])
        with patch.object(PushDevice, "find", find), patch.object(PushDevice, "enabled", MagicMock(), create=True):
            result = await PushDevicesRepository().get_enabled_tokens()

        assert result == ["a"]
        find.return_value.project.assert_called_once_with(_DeviceToken)
