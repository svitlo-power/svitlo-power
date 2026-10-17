"""Tests for app/services/push/service.py."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.push.service import PushService
from app.services.push.fcm_sender import FcmSendResult, PushMessage
from app.models.api import PushDeviceRegisterRequest, PushDeviceSubscriptionsRequest
from shared.models.localizable_value import LocalizableValue
from shared.models.push_device import PushDevice, PushPlatform
from shared.models.push_topic import PushTopic
from app.services.push.topics import DEFAULT_TOPICS


def _device(token="tok-1", **kwargs) -> PushDevice:
    return PushDevice(id=PydanticObjectId(), token=token, platform=PushPlatform.Android, **kwargs)


def _repo(device=None, devices=None):
    repo = MagicMock()
    repo.get_device = AsyncMock(return_value=device)
    repo.get_device_by_id = AsyncMock(return_value=device)
    repo.save_device = AsyncMock(side_effect=lambda d: d)
    repo.delete_device = AsyncMock(return_value=True)
    repo.delete_devices = AsyncMock(side_effect=lambda tokens: len(tokens))
    repo.get_enabled_devices = AsyncMock(return_value=devices or [])
    repo.get_all_devices = AsyncMock(return_value=devices or [])
    repo.get_topic_devices = AsyncMock(return_value=devices or [])
    repo.count_topic_devices = AsyncMock(return_value=len(devices or []))
    return repo


def _topic(key="schedule_changes", enabled=True) -> PushTopic:
    return PushTopic(
        key=key, enabled=enabled,
        name=LocalizableValue({"uk": "Назва", "en": "Name"}),
        description=LocalizableValue({"uk": "Опис", "en": "Description"}),
    )


def _topics(topics=None):
    topics = topics or []
    repo = MagicMock()
    repo.get_all_topics = AsyncMock(return_value=topics)
    repo.get_enabled_topics = AsyncMock(return_value=[t for t in topics if t.enabled])
    repo.get_topic = AsyncMock(side_effect=lambda key: next((t for t in topics if t.key == key), None))
    repo.add_topic = AsyncMock(side_effect=lambda t: t)
    repo.set_enabled = AsyncMock(return_value=True)
    return repo


class TestPushServiceRegister:
    @pytest.mark.asyncio
    async def test_register_creates_new_device(self):
        repo = _repo(device=None)

        async def save(device):
            device.id = PydanticObjectId()
            return device
        repo.save_device = AsyncMock(side_effect=save)
        service = PushService(repo, _topics(), MagicMock())

        result = await service.register_device(PushDeviceRegisterRequest(
            token="tok-1", platform="web", language="en", appVersion="2.1.1",
        ))

        saved = repo.save_device.call_args.args[0]
        assert saved.token == "tok-1"
        assert saved.platform == PushPlatform.Web
        assert result.language == "en"
        assert result.app_version == "2.1.1"

    @pytest.mark.asyncio
    async def test_register_keeps_existing_subscriptions(self):
        existing = _device(disabled_topics=["schedule"])
        repo = _repo(device=existing)
        service = PushService(repo, _topics(), MagicMock())

        result = await service.register_device(PushDeviceRegisterRequest(token="tok-1", platform="android"))

        assert result.disabled_topics == ["schedule"]
        assert repo.save_device.call_args.args[0] is existing


class TestPushServiceSubscriptions:
    @pytest.mark.asyncio
    async def test_update_subscriptions_deduplicates(self):
        building = PydanticObjectId()
        repo = _repo(device=_device())
        service = PushService(repo, _topics(), MagicMock())

        result = await service.update_subscriptions(PushDeviceSubscriptionsRequest(
            token="tok-1", enabled=False, disabledTopics=["a", "a", "b"], buildings=[building, building],
        ))

        assert result.enabled is False
        assert result.disabled_topics == ["a", "b"]
        assert result.buildings == [building]

    @pytest.mark.asyncio
    async def test_update_subscriptions_unknown_device(self):
        service = PushService(_repo(device=None), _topics(), MagicMock())
        result = await service.update_subscriptions(PushDeviceSubscriptionsRequest(token="missing"))
        assert result is None


class TestPushServiceSend:
    @pytest.mark.asyncio
    async def test_send_to_all_removes_invalid_tokens(self):
        repo = _repo(devices=[_device("a"), _device("b")])
        sender = MagicMock()
        sender.send = AsyncMock(return_value=FcmSendResult(success_count=1, failure_count=1, invalid_tokens=["b"]))
        service = PushService(repo, _topics(), sender)

        result = await service.send_to_all(PushMessage(title="t", body="b"))

        assert sender.send.call_args.args[0] == ["a", "b"]
        repo.delete_devices.assert_called_once_with(["b"])
        assert (result.success_count, result.failure_count, result.removed_count) == (1, 1, 1)

    @pytest.mark.asyncio
    async def test_send_to_device_not_found(self):
        service = PushService(_repo(device=None), _topics(), MagicMock())
        assert await service.send_to_device(PydanticObjectId(), PushMessage(title="t", body="b")) is None


class TestPushServiceTopics:
    @pytest.mark.asyncio
    async def test_ensure_default_topics_creates_only_missing(self):
        existing = _topic(DEFAULT_TOPICS[0].key, enabled=False)
        topics = _topics([existing])
        service = PushService(_repo(), topics, MagicMock())

        await service.ensure_default_topics()

        created = [c.args[0].key for c in topics.add_topic.call_args_list]
        assert created == [t.key for t in DEFAULT_TOPICS[1:]]
        assert existing.enabled is False

    @pytest.mark.asyncio
    async def test_send_to_topic_uses_subscribers(self):
        repo = _repo(devices=[_device("a")])
        sender = MagicMock()
        sender.send = AsyncMock(return_value=FcmSendResult(success_count=1))
        service = PushService(repo, _topics([_topic("schedule_changes")]), sender)

        result = await service.send_to_topic("schedule_changes", PushMessage(title="t", body="b"))

        repo.get_topic_devices.assert_called_once_with("schedule_changes")
        assert sender.send.call_args.args[1].data["topic"] == "schedule_changes"
        assert result.success_count == 1

    @pytest.mark.asyncio
    async def test_send_to_disabled_topic_sends_nothing(self):
        sender = MagicMock()
        sender.send = AsyncMock()
        service = PushService(_repo(devices=[_device("a")]), _topics([_topic(enabled=False)]), sender)

        result = await service.send_to_topic("schedule_changes", PushMessage(title="t", body="b"))

        sender.send.assert_not_called()
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_send_to_unknown_topic(self):
        service = PushService(_repo(), _topics(), MagicMock())
        assert await service.send_to_topic("missing", PushMessage(title="t", body="b")) is None

    @pytest.mark.asyncio
    async def test_admin_topics_include_subscriber_count(self):
        service = PushService(_repo(devices=[_device("a"), _device("b")]), _topics([_topic()]), MagicMock())

        result = await service.get_all_topics()

        assert result[0].subscribers == 2
        assert result[0].name == {"uk": "Назва", "en": "Name"}
