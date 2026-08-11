"""Tests for shared/services/events/service.py."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.services.events.service import EventsService
from shared.services.events.models import EventItem, EventsServiceConfig
from shared.services.events.events_transport import LocalTransport
from shared.services.events.redis_transport import RedisTransport
from shared.bounded_queue import BoundedQueue


class TestEventsServiceInit:
    def test_debug_mode_uses_local_transport(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        assert isinstance(service.transport, LocalTransport)

    def test_non_debug_mode_uses_redis_transport(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=False)
        with patch("shared.services.events.redis_transport.Redis.from_url"):
            service = EventsService(config)
        assert isinstance(service.transport, RedisTransport)

    def test_redis_transport_configured_with_channels(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=False)
        with patch("shared.services.events.redis_transport.Redis.from_url"):
            service = EventsService(config)
        assert service.transport.redis_uri == "redis://localhost:6379"
        assert EventsService.REDIS_PUBLIC_CHANNEL in service.transport.channels
        assert EventsService.REDIS_PRIVATE_CHANNEL in service.transport.channels

    def test_public_clients_is_empty_set(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        assert service._public_clients == set()

    def test_private_clients_is_empty_set(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        assert service._private_clients == set()

    def test_subscriber_task_is_none(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        assert service._subscriber_task is None


class TestEventsServiceChannels:
    def test_public_channel_name(self):
        assert EventsService.REDIS_PUBLIC_CHANNEL == "sse_public"

    def test_private_channel_name(self):
        assert EventsService.REDIS_PRIVATE_CHANNEL == "sse_private"


class TestEventsServiceStart:
    @pytest.mark.asyncio
    async def test_start_creates_subscriber_task(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        with patch.object(service.transport, "start_subscriber", new_callable=AsyncMock):
            await service.start()
            assert service._subscriber_task is not None

    @pytest.mark.asyncio
    async def test_start_is_idempotent(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        with patch.object(service.transport, "start_subscriber", new_callable=AsyncMock):
            await service.start()
            first_task = service._subscriber_task
            await service.start()
            assert service._subscriber_task is first_task


class TestEventsServiceShutdown:
    @pytest.mark.asyncio
    async def test_request_shutdown_sends_shutdown_event(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_public_client(q)
        service.add_private_client(q)

        with patch.object(q, "put_nowait") as mock_put:
            await service.request_shutdown()
            assert mock_put.call_count == 2

    @pytest.mark.asyncio
    async def test_shutdown_calls_transport_stop(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=False)
        with patch("shared.services.events.redis_transport.Redis.from_url"):
            service = EventsService(config)
        with patch.object(service.transport, "stop", new_callable=AsyncMock) as mock_stop:
            await service.shutdown()
            mock_stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_shutdown_calls_cleanup_all(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        with patch.object(service, "cleanup_all", new_callable=AsyncMock) as mock_cleanup:
            await service.shutdown()
            mock_cleanup.assert_awaited_once()


class TestEventsServiceClientManagement:
    def test_add_public_client(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_public_client(q)
        assert q in service._public_clients

    def test_add_private_client(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_private_client(q)
        assert q in service._private_clients

    def test_remove_client_from_public(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_public_client(q)
        service.remove_client(q)
        assert q not in service._public_clients

    def test_remove_client_from_private(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_private_client(q)
        service.remove_client(q)
        assert q not in service._private_clients


class TestEventsServiceBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_public(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        with patch.object(service.transport, "publish", new_callable=AsyncMock) as mock_publish:
            await service.broadcast_public("test_type", {"key": "value"})
            mock_publish.assert_awaited_once()
            call_args = mock_publish.call_args
            assert call_args.args[0] == EventsService.REDIS_PUBLIC_CHANNEL
            assert call_args.args[1].type == "test_type"
            assert call_args.args[1].data == {"key": "value"}
            assert call_args.args[1].private is False

    @pytest.mark.asyncio
    async def test_broadcast_private(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        with patch.object(service.transport, "publish", new_callable=AsyncMock) as mock_publish:
            await service.broadcast_private("test_type", {"key": "value"})
            mock_publish.assert_awaited_once()
            call_args = mock_publish.call_args
            assert call_args.args[0] == EventsService.REDIS_PRIVATE_CHANNEL
            assert call_args.args[1].type == "test_type"
            assert call_args.args[1].data == {"key": "value"}
            assert call_args.args[1].private is True


class TestEventsServiceHandleIncoming:
    @pytest.mark.asyncio
    async def test_handle_public_channel_event(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_public_client(q)

        event = EventItem(type="test", data={}, private=False)
        with patch.object(q, "put_nowait") as mock_put:
            await service._handle_incoming_event(EventsService.REDIS_PUBLIC_CHANNEL, event)
            mock_put.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_private_channel_event(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_private_client(q)

        event = EventItem(type="test", data={}, private=True)
        with patch.object(q, "put_nowait") as mock_put:
            await service._handle_incoming_event(EventsService.REDIS_PRIVATE_CHANNEL, event)
            mock_put.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_handle_unknown_channel_does_nothing(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q = BoundedQueue()
        service.add_public_client(q)

        event = EventItem(type="test", data={}, private=False)
        with patch.object(q, "put_nowait") as mock_put:
            await service._handle_incoming_event("unknown_channel", event)
            mock_put.assert_not_called()


class TestEventsServiceCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_all_sends_none_to_clients(self):
        config = EventsServiceConfig(redis_uri="redis://localhost:6379", is_debug=True)
        service = EventsService(config)
        q1 = BoundedQueue()
        q2 = BoundedQueue()
        service.add_public_client(q1)
        service.add_private_client(q2)

        with patch.object(q1, "put_nowait") as mock_put1, \
             patch.object(q2, "put_nowait") as mock_put2:
            await service.cleanup_all()
            mock_put1.assert_called_once_with(None)
            mock_put2.assert_called_once_with(None)
