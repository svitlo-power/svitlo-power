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
    async def test_publish_with_none_handler_does_nothing(self):
        transport = LocalTransport()
        transport.handler = None
        event = EventItem(type="test", data={}, private=False)
        # Should not raise, just return None
        result = await transport.publish("test_channel", event)
        assert result is None

    @pytest.mark.asyncio
    async def test_start_subscriber_sets_handler(self):
        transport = LocalTransport()

        async def handler(channel, event):
            pass

        await transport.start_subscriber(handler)
        assert transport.handler == handler

    @pytest.mark.asyncio
    async def test_start_subscriber_returns_none(self):
        transport = LocalTransport()

        async def handler(channel, event):
            pass

        result = await transport.start_subscriber(handler)
        assert result is None

    @pytest.mark.asyncio
    async def test_start_subscriber_overwrites_handler(self):
        transport = LocalTransport()

        async def handler1(channel, event):
            pass

        async def handler2(channel, event):
            pass

        await transport.start_subscriber(handler1)
        assert transport.handler == handler1
        await transport.start_subscriber(handler2)
        assert transport.handler == handler2

    @pytest.mark.asyncio
    async def test_publish_with_handler_calls_handler(self):
        transport = LocalTransport()
        received = []

        async def handler(channel, event):
            received.append((channel, event))

        transport.handler = handler
        event = EventItem(type="test", data={"key": "value"}, private=False)
        await transport.publish("test_channel", event)
        assert len(received) == 1
        assert received[0][0] == "test_channel"
        assert received[0][1] == event

    @pytest.mark.asyncio
    async def test_start_subscriber_calls_handler_assignment(self):
        """Test that start_subscriber assigns the handler (covers line 15)."""
        transport = LocalTransport()

        async def handler(channel, event):
            pass

        await transport.start_subscriber(handler)
        assert transport.handler == handler
