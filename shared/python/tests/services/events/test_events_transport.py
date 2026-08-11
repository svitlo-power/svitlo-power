"""Tests for shared/services/events/events_transport.py."""
import pytest

from shared.services.events.events_transport import EventsTransport, LocalTransport
from shared.services.events.models import EventItem


class TestEventsTransport:
    def test_is_abstract(self):
        assert getattr(EventsTransport, "__abstractmethods__", set())

    def test_has_publish_method(self):
        assert hasattr(EventsTransport, "publish")

    def test_has_start_subscriber_method(self):
        assert hasattr(EventsTransport, "start_subscriber")

    def test_cannot_instantiate_abstract(self):
        with pytest.raises(TypeError):
            EventsTransport()


class TestLocalTransport:
    def test_is_subclass_of_events_transport(self):
        assert issubclass(LocalTransport, EventsTransport)

    @pytest.mark.asyncio
    async def test_publish_calls_handler(self):
        transport = LocalTransport()
        received = []

        async def handler(channel, event):
            received.append((channel, event))

        await transport.start_subscriber(handler)
        event = EventItem(type="test", data={"key": "value"}, private=False)
        await transport.publish("test_channel", event)
        assert len(received) == 1
        assert received[0][0] == "test_channel"
        assert received[0][1] == event

    @pytest.mark.asyncio
    async def test_publish_without_handler_raises_attribute_error(self):
        transport = LocalTransport()
        event = EventItem(type="test", data={}, private=False)
        with pytest.raises(AttributeError):
            await transport.publish("test_channel", event)

    @pytest.mark.asyncio
    async def test_start_subscriber_sets_handler(self):
        transport = LocalTransport()

        async def handler(channel, event):
            pass

        await transport.start_subscriber(handler)
        assert transport.handler == handler
