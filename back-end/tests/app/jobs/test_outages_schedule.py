"""Tests for app/jobs/outages_schedule.py."""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs.outages_schedule import register
from app.services import OutagesScheduleService


class TestRegister:
    def test_register_adds_update_outages_schedule_job(self):
        """Test that register adds update_outages_schedule job to scheduler."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.update = AsyncMock()

        def get_side_effect(cls):
            if cls is OutagesScheduleService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Verify scheduler.add_job was called
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "update_outages_schedule"
        assert call_kwargs["trigger"] == "interval"
        assert call_kwargs["minutes"] == 5
        assert call_kwargs["max_instances"] == 1

    def test_register_gets_scheduler_from_injector(self):
        """Test that register gets AsyncIOScheduler from injector."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.update = AsyncMock()

        def get_side_effect(cls):
            if cls is OutagesScheduleService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        injector.get.assert_called()

    def test_update_outages_schedule_job_calls_service(self):
        """Test that update_outages_schedule job calls OutagesScheduleService.update."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.update = AsyncMock()

        def get_side_effect(cls):
            if cls is OutagesScheduleService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the job function and execute it
        call_kwargs = scheduler.add_job.call_args[1]
        job_func = call_kwargs["func"]

        # Run the async job function
        asyncio.run(job_func())

        # Verify the service was called with correct args
        mock_service.update.assert_called_once_with(25, 902)