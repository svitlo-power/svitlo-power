"""Tests for app/jobs/sse.py."""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs.sse import register
from shared.services import EventsService


class TestRegister:
    def test_register_adds_send_ping_job_when_interval_positive(self):
        """Test that register adds send_ping job when SSE_PING_INTERVAL > 0."""
        settings = MagicMock()
        settings.SSE_PING_INTERVAL = 45
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.broadcast_public = AsyncMock()

        def get_side_effect(cls):
            if cls is EventsService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was called
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "send_ping"
        assert call_kwargs["trigger"] == "interval"
        assert call_kwargs["seconds"] == 45

    def test_register_does_not_add_job_when_interval_zero(self):
        """Test that register does not add job when SSE_PING_INTERVAL is 0."""
        settings = MagicMock()
        settings.SSE_PING_INTERVAL = 0
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.broadcast_public = AsyncMock()

        def get_side_effect(cls):
            if cls is EventsService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was NOT called
        scheduler.add_job.assert_not_called()

    def test_register_gets_scheduler_from_injector(self):
        """Test that register gets AsyncIOScheduler from injector."""
        settings = MagicMock()
        settings.SSE_PING_INTERVAL = 45
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.broadcast_public = AsyncMock()

        def get_side_effect(cls):
            if cls is EventsService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        injector.get.assert_called()

    def test_send_ping_job_calls_service(self):
        """Test that send_ping job calls EventsService.broadcast_public."""
        settings = MagicMock()
        settings.SSE_PING_INTERVAL = 45
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.broadcast_public = AsyncMock()

        def get_side_effect(cls):
            if cls is EventsService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the job function and execute it
        call_kwargs = scheduler.add_job.call_args[1]
        job_func = call_kwargs["func"]

        # Run the async job function
        asyncio.run(job_func())

        # Verify the service was called
        mock_service.broadcast_public.assert_called_once_with("ping")