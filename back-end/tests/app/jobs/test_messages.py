"""Tests for app/jobs/messages.py."""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs.messages import register
from app.services import MessageProcessorService


class TestRegister:
    def test_register_adds_periodic_send_message_job(self):
        """Test that register adds periodic_send_message job to scheduler."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()
        injector.get.return_value = scheduler

        mock_service = MagicMock()
        mock_service.periodic_send = AsyncMock()

        def get_side_effect(cls):
            if cls is MessageProcessorService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was called
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "periodic_send_message"
        assert call_kwargs["trigger"] == "interval"
        assert call_kwargs["seconds"] == 60

    def test_register_gets_scheduler_from_injector(self):
        """Test that register gets AsyncIOScheduler from injector."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()
        injector.get.return_value = scheduler

        mock_service = MagicMock()
        mock_service.periodic_send = AsyncMock()

        def get_side_effect(cls):
            if cls is MessageProcessorService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        injector.get.assert_called()

    def test_periodic_send_message_job_calls_service(self):
        """Test that periodic_send_message job calls MessageProcessorService.periodic_send."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.periodic_send = AsyncMock()

        def get_side_effect(cls):
            if cls is MessageProcessorService:
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
        mock_service.periodic_send.assert_called_once()