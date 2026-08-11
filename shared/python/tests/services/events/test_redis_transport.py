"""Tests for shared/services/events/redis_transport.py."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.services.events.redis_transport import RedisTransport
from shared.services.events.models import EventItem


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    mock = MagicMock()
    mock.publish = AsyncMock()
    mock.close = AsyncMock()
    mock.pubsub = MagicMock()
    return mock


@pytest.fixture
def transport(mock_redis):
    """Create a RedisTransport with a mocked Redis client."""
    with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
        t = RedisTransport("redis://localhost:6379", "channel1", "channel2")
    return t


class TestRedisTransportInit:
    def test_init_sets_redis_uri(self, mock_redis):
        with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
            transport = RedisTransport("redis://localhost:6379", "channel1", "channel2")
        assert transport.redis_uri == "redis://localhost:6379"

    def test_init_sets_channels(self, mock_redis):
        with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
            transport = RedisTransport("redis://localhost:6379", "channel1", "channel2")
        assert transport.channels == ("channel1", "channel2")

    def test_init_subscriber_task_is_none(self, mock_redis):
        with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
            transport = RedisTransport("redis://localhost:6379", "channel1")
        assert transport._subscriber_task is None

    def test_init_stopped_is_false(self, mock_redis):
        with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
            transport = RedisTransport("redis://localhost:6379", "channel1")
        assert transport._stopped is False


class TestRedisTransportPublish:
    @pytest.mark.asyncio
    async def test_publish_success(self, transport, mock_redis):
        event = EventItem(type="test", data={"key": "value"}, private=False)
        await transport.publish("channel1", event)

        mock_redis.publish.assert_awaited_once()
        call_args = mock_redis.publish.call_args
        assert call_args.args[0] == "channel1"
        payload = json.loads(call_args.args[1])
        assert payload["type"] == "test"
        assert payload["data"] == {"key": "value"}
        assert payload["private"] is False

    @pytest.mark.asyncio
    async def test_publish_retries_on_connection_error(self, transport, mock_redis):
        call_count = [0]

        async def mock_publish(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                from redis.asyncio import ConnectionError
                raise ConnectionError("Connection failed")
            return

        mock_redis.publish = mock_publish

        # Also patch Redis.from_url so the retry path gets the same mock
        with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
            event = EventItem(type="test", data={}, private=False)
            with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock):
                await transport.publish("channel1", event)

        assert call_count[0] == 2


class TestRedisTransportSubscriber:
    @pytest.mark.asyncio
    async def test_start_subscriber_creates_task(self, transport):
        with patch.object(transport, "_subscriber_loop", new_callable=AsyncMock):
            await transport.start_subscriber(lambda ch, ev: None)
            assert transport._subscriber_task is not None

    @pytest.mark.asyncio
    async def test_start_subscriber_idempotent(self, transport):
        with patch.object(transport, "_subscriber_loop", new_callable=AsyncMock):
            await transport.start_subscriber(lambda ch, ev: None)
            first_task = transport._subscriber_task
            await transport.start_subscriber(lambda ch, ev: None)
            assert transport._subscriber_task is first_task


class TestRedisTransportStop:
    @pytest.mark.asyncio
    async def test_stop_sets_stopped_flag(self, transport):
        await transport.stop()
        assert transport._stopped is True

    @pytest.mark.asyncio
    async def test_stop_closes_redis(self, transport, mock_redis):
        await transport.stop()
        mock_redis.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_cancels_subscriber_task(self, transport):
        mock_task = MagicMock()
        mock_task.cancel = MagicMock()
        transport._subscriber_task = mock_task
        await transport.stop()
        mock_task.cancel.assert_called_once()
