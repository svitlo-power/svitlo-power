"""Tests for app/services/push/dispatcher.py."""
import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.models.api import PushSendResult
from app.services.push.dispatcher import PushEventDispatcher
from app.services.push.events import PushEvent
from app.services.push.templates import PushTemplatesService
from app.services.push.topics import POWER_STATUS
from shared.models.localizable_value import LocalizableValue
from shared.models.push_delivery import PushDeliveryStatus
from shared.models.push_template import PushTemplate
from shared.models.push_topic import PushTopic
from shared.repositories.interfaces.push_devices import PushRecipient


def _settings():
    settings = MagicMock()
    settings.BOT_TIMEZONE = "Europe/Kyiv"
    settings.PUSH_POWER_DEBOUNCE_SECONDS = 60
    return settings


def _topic(enabled=True):
    return PushTopic(
        key=POWER_STATUS, enabled=enabled,
        name=LocalizableValue({"en": "Power"}), description=LocalizableValue({"en": "Power"}),
    )


def _template(**kwargs):
    values = {
        "topic": POWER_STATUS,
        "title": LocalizableValue({"uk": "{{ building.name }}: світла немає", "en": "{{ building.name }}: power is out"}),
        "body": LocalizableValue({"uk": "Б", "en": "B"}),
        "route": "/buildings/{{ building.id }}",
    }
    values.update(kwargs)
    return PushTemplate(**values)


class _Deliveries:
    """In-memory delivery store with the unique dedup_key behavior of the Mongo index."""
    def __init__(self):
        self.items = {}
        self.save = AsyncMock(side_effect=self._save)

    async def try_insert(self, delivery):
        if delivery.dedup_key in self.items:
            return False
        self.items[delivery.dedup_key] = delivery
        return True

    async def _save(self, delivery):
        self.items[delivery.dedup_key] = delivery
        return delivery

    async def get_recent(self, limit):
        return list(self.items.values())[:limit]


def _dispatcher(
    topic=None,
    template=None,
    recipients=None,
    send_result=None,
):
    push = MagicMock()
    push.send_to_tokens = AsyncMock(side_effect=lambda tokens, message: send_result or PushSendResult(
        success_count=len(tokens), failure_count=0, removed_count=0,
    ))

    template_repo = MagicMock()
    template_repo.get_template = AsyncMock(return_value=template if template is not None else _template())
    templates = PushTemplatesService(template_repo, _settings())

    topics = MagicMock()
    topics.get_topic = AsyncMock(return_value=topic if topic is not None else _topic())

    devices = MagicMock()
    devices.get_topic_recipients = AsyncMock(return_value=recipients if recipients is not None else [
        PushRecipient("t-uk-1", "uk"),
        PushRecipient("t-uk-2", "uk"),
        PushRecipient("t-en", "en"),
        PushRecipient("t-de", "de"),
    ])

    deliveries = _Deliveries()
    dispatcher = PushEventDispatcher(push, templates, topics, devices, deliveries)
    return dispatcher, push, deliveries


def _event(key="power:1:off:2026-10-22T10:00"):
    building_id = PydanticObjectId()
    return PushEvent(
        topic=POWER_STATUS,
        dedup_key=key,
        context={"building": {"id": str(building_id), "name": {"uk": "Будинок", "en": "Building"}}},
        data={"buildingId": str(building_id)},
        summary={"building": "Building"},
        building_id=building_id,
    )


class TestDispatch:
    @pytest.mark.asyncio
    async def test_sends_one_multicast_per_language(self):
        dispatcher, push, _ = _dispatcher()

        delivery = await dispatcher.dispatch(_event())

        calls = { tuple(c.args[0]): c.args[1] for c in push.send_to_tokens.call_args_list }
        # Unsupported "de" falls back to the default language (en)
        assert set(calls) == {("t-uk-1", "t-uk-2"), ("t-en", "t-de")}
        assert calls[("t-uk-1", "t-uk-2")].title == "Будинок: світла немає"
        assert calls[("t-en", "t-de")].title == "Building: power is out"
        assert delivery.status == PushDeliveryStatus.Sent
        assert delivery.recipients == 4
        assert delivery.recipients_by_language == {"uk": 2, "en": 2}
        assert delivery.success_count == 4

    @pytest.mark.asyncio
    async def test_payload_has_topic_route_and_event_data(self):
        dispatcher, push, _ = _dispatcher(recipients=[PushRecipient("t", "en")])
        event = _event()

        await dispatcher.dispatch(event)

        message = push.send_to_tokens.call_args.args[1]
        building_id = event.data["buildingId"]
        assert message.data == {"buildingId": building_id, "topic": POWER_STATUS, "route": f"/buildings/{building_id}"}

    @pytest.mark.asyncio
    async def test_duplicate_event_is_sent_once(self):
        dispatcher, push, deliveries = _dispatcher()

        first = await dispatcher.dispatch(_event())
        second = await dispatcher.dispatch(_event())

        assert first is not None
        assert second is None
        assert push.send_to_tokens.await_count == 2  # two languages of the first event only
        assert len(deliveries.items) == 1

    @pytest.mark.asyncio
    async def test_concurrent_duplicates_are_sent_once(self):
        dispatcher, push, _ = _dispatcher(recipients=[PushRecipient("t", "en")])

        await asyncio.gather(*(dispatcher.dispatch(_event()) for _ in range(5)))

        assert push.send_to_tokens.await_count == 1

    @pytest.mark.asyncio
    async def test_disabled_topic_is_skipped_and_recorded(self, caplog):
        dispatcher, push, deliveries = _dispatcher(topic=_topic(enabled=False))

        with caplog.at_level(logging.INFO):
            delivery = await dispatcher.dispatch(_event())

        push.send_to_tokens.assert_not_called()
        assert delivery.status == PushDeliveryStatus.SkippedTopicDisabled
        assert deliveries.items[delivery.dedup_key].status == PushDeliveryStatus.SkippedTopicDisabled
        assert "topic_disabled" in caplog.text

    @pytest.mark.asyncio
    async def test_disabled_template_is_skipped(self):
        dispatcher, push, _ = _dispatcher(template=_template(enabled=False))

        delivery = await dispatcher.dispatch(_event())

        push.send_to_tokens.assert_not_called()
        assert delivery.status == PushDeliveryStatus.SkippedTemplateDisabled

    @pytest.mark.asyncio
    async def test_false_condition_is_skipped(self):
        dispatcher, push, _ = _dispatcher(template=_template(should_send="{{ building.name == 'Other' }}"))

        delivery = await dispatcher.dispatch(_event())

        push.send_to_tokens.assert_not_called()
        assert delivery.status == PushDeliveryStatus.SkippedCondition

    @pytest.mark.asyncio
    async def test_no_recipients(self):
        dispatcher, push, _ = _dispatcher(recipients=[])

        delivery = await dispatcher.dispatch(_event())

        push.send_to_tokens.assert_not_called()
        assert delivery.status == PushDeliveryStatus.NoRecipients

    @pytest.mark.asyncio
    async def test_broken_language_template_does_not_block_others(self):
        template = _template(title=LocalizableValue({"uk": "{{ 1 / 0 }}", "en": "ok"}))
        dispatcher, push, _ = _dispatcher(template=template)

        delivery = await dispatcher.dispatch(_event())

        assert push.send_to_tokens.await_count == 1
        assert push.send_to_tokens.call_args.args[0] == ["t-en", "t-de"]
        assert delivery.status == PushDeliveryStatus.Sent
        assert delivery.failure_count == 2
        assert delivery.error.startswith("uk:")

    @pytest.mark.asyncio
    async def test_fcm_failures_and_removed_tokens_are_recorded(self):
        dispatcher, _, _ = _dispatcher(
            recipients=[PushRecipient("a", "en"), PushRecipient("b", "en")],
            send_result=PushSendResult(success_count=0, failure_count=2, removed_count=1),
        )

        delivery = await dispatcher.dispatch(_event())

        assert delivery.status == PushDeliveryStatus.Failed
        assert delivery.failure_count == 2
        assert delivery.invalid_removed == 1

    @pytest.mark.asyncio
    async def test_unexpected_error_is_recorded_as_failed(self):
        dispatcher, push, _ = _dispatcher()
        push.send_to_tokens.side_effect = RuntimeError("boom")

        delivery = await dispatcher.dispatch(_event())

        assert delivery.status == PushDeliveryStatus.Failed
        assert delivery.error == "boom"

    @pytest.mark.asyncio
    async def test_logs_and_records_contain_no_tokens(self, caplog):
        dispatcher, _, deliveries = _dispatcher()

        with caplog.at_level(logging.DEBUG):
            await dispatcher.dispatch(_event())

        record = deliveries.items["power:1:off:2026-10-22T10:00"].model_dump_json()
        for token in ("t-uk-1", "t-uk-2", "t-en", "t-de"):
            assert token not in caplog.text
            assert token not in record


class TestFire:
    @pytest.mark.asyncio
    async def test_fire_runs_in_background_and_swallows_errors(self, caplog):
        dispatcher, push, _ = _dispatcher()
        dispatcher.dispatch = AsyncMock(side_effect=RuntimeError("boom"))

        task = dispatcher.fire(_event())
        await task

        assert task.exception() is None
        assert "boom" in caplog.text

    @pytest.mark.asyncio
    async def test_recent_deliveries(self):
        dispatcher, _, _ = _dispatcher()
        await dispatcher.dispatch(_event())

        result = await dispatcher.get_recent_deliveries()

        assert len(result) == 1
        assert result[0].status == PushDeliveryStatus.Sent
