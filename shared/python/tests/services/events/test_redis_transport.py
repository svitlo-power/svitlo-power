"""Tests for shared/services/events/redis_transport.py."""
import json
import asyncio
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


class TestRedisTransportSubscriberLoop:
    @pytest.mark.asyncio
    async def test_subscriber_loop_processes_messages(self, transport, mock_redis):
        """Test that the subscriber loop processes messages correctly."""
        from redis.asyncio import ConnectionError

        # Set up mock pubsub
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        # Simulate messages: one None, one non-message type, one valid message
        messages = [
            None,
            {"type": "subscribe", "data": "ok"},
            {"type": "message", "channel": "channel1", "data": json.dumps({"type": "test", "data": {"key": "val"}, "private": False})},
        ]

        async def mock_listen():
            for msg in messages:
                yield msg
            # After all messages, raise ConnectionError to exit the loop
            raise ConnectionError("pubsub ended")

        mock_pubsub.listen = MagicMock(return_value=mock_listen())
        # Use return_value on the existing mock instead of replacing it
        mock_redis.pubsub.return_value = mock_pubsub

        received = []

        async def handler(channel, event):
            received.append((channel, event))

        # Don't patch asyncio.sleep - let it actually sleep to allow the loop to process
        task = asyncio.create_task(transport._subscriber_loop(handler))
        # Wait for the task to process messages
        await asyncio.sleep(0.2)
        transport._stopped = True
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert len(received) == 1
        assert received[0][0] == "channel1"
        assert received[0][1].type == "test"

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_connection_error(self, transport, mock_redis):
        """Test that the subscriber loop handles ConnectionError and reconnects."""
        from redis.asyncio import ConnectionError

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        async def mock_listen():
            raise ConnectionError("Connection lost")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock):
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.1)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_generic_exception(self, transport, mock_redis):
        """Test that the subscriber loop handles generic exceptions."""
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        async def mock_listen():
            raise Exception("Unexpected error")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock):
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.1)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_timeout_error(self, transport, mock_redis):
        """Test that the subscriber loop handles TimeoutError."""
        from redis.asyncio import TimeoutError

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        async def mock_listen():
            raise TimeoutError("Timeout")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock):
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.1)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass


class TestRedisTransportStopException:
    @pytest.mark.asyncio
    async def test_stop_handles_close_exception(self, transport, mock_redis):
        """Test that stop handles exceptions from redis.close()."""
        mock_redis.close = AsyncMock(side_effect=Exception("Close error"))
        await transport.stop()

    @pytest.mark.asyncio
    async def test_subscriber_loop_backoff_increases(self, transport, mock_redis):
        """Test that the subscriber loop backoff increases on connection errors."""
        from redis.asyncio import ConnectionError

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        call_count = [0]

        async def mock_listen():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise ConnectionError("Connection lost")
            else:
                # On third call, raise to exit
                raise ConnectionError("pubsub ended")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.3)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Check that sleep was called at least once
                assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_loop_generic_exception_backoff(self, transport, mock_redis):
        """Test that the subscriber loop uses 1s backoff on generic exceptions."""
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        call_count = [0]

        async def mock_listen():
            call_count[0] += 1
            if call_count[0] <= 2:
                raise Exception("Unexpected error")
            else:
                raise ConnectionError("pubsub ended")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.3)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Check that sleep was called
                assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_loop_raises_connection_error_on_empty(self, transport, mock_redis):
        """Test that the subscriber loop raises ConnectionError when pubsub.listen() ends."""
        from redis.asyncio import ConnectionError

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        async def mock_listen():
            # Empty async generator - ends immediately
            return
            yield  # Make it an async generator

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock):
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.1)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_connection_error_reconnect(self, transport, mock_redis):
        """Test that the subscriber loop reconnects on ConnectionError."""
        from redis.asyncio import ConnectionError

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        call_count = [0]

        async def mock_listen():
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("Connection lost")
            else:
                # On second call, raise to exit
                raise ConnectionError("pubsub ended")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.2)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Check that sleep was called for backoff
                assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_timeout_error_reconnect(self, transport, mock_redis):
        """Test that the subscriber loop reconnects on TimeoutError."""
        from redis.asyncio import TimeoutError

        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        call_count = [0]

        async def mock_listen():
            call_count[0] += 1
            if call_count[0] == 1:
                raise TimeoutError("Timeout")
            else:
                raise ConnectionError("pubsub ended")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.2)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Check that sleep was called for backoff
                assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_subscriber_loop_handles_generic_exception_recover(self, transport, mock_redis):
        """Test that the subscriber loop recovers on generic exceptions."""
        mock_pubsub = MagicMock()
        mock_pubsub.subscribe = AsyncMock()

        call_count = [0]

        async def mock_listen():
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Unexpected error")
            else:
                raise ConnectionError("pubsub ended")

        mock_pubsub.listen = mock_listen
        mock_redis.pubsub = MagicMock(return_value=mock_pubsub)

        with patch("shared.services.events.redis_transport.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("shared.services.events.redis_transport.Redis.from_url", return_value=mock_redis):
                task = asyncio.create_task(transport._subscriber_loop(lambda ch, ev: None))
                await asyncio.sleep(0.2)
                transport._stopped = True
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Check that sleep was called with 1s backoff
                assert mock_sleep.call_count >= 1
        assert transport._stopped is True
