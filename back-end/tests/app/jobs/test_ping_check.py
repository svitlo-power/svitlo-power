"""Tests for app/jobs/ping_check.py."""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs.ping_check import register
from app.services.interfaces import IExtDeviceService


class TestRegister:
    def test_register_adds_ping_check_job(self):
        """Test that register adds ping_check job to scheduler."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.check_pings = AsyncMock()

        def get_side_effect(cls):
            if cls is IExtDeviceService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was called
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "ping_check"
        assert call_kwargs["trigger"] == "interval"
        assert call_kwargs["seconds"] == 30

    def test_register_gets_scheduler_from_injector(self):
        """Test that register gets AsyncIOScheduler from injector."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.check_pings = AsyncMock()

        def get_side_effect(cls):
            if cls is IExtDeviceService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        injector.get.assert_called()

    def test_ping_check_job_calls_service(self):
        """Test that ping_check job calls IExtDeviceService.check_pings."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.check_pings = AsyncMock()

        def get_side_effect(cls):
            if cls is IExtDeviceService:
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
        mock_service.check_pings.assert_called_once()