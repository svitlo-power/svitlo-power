"""Tests for app/jobs/maintenance.py."""
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs.maintenance import register
from app.services import MaintenanceService


class TestRegister:
    def test_register_adds_delete_old_data_job(self):
        """Test that register adds delete_old_data job to scheduler."""
        settings = MagicMock()
        settings.STATISTIC_KEEP_DAYS = 3
        injector = MagicMock()
        scheduler = MagicMock()
        injector.get.return_value = scheduler

        mock_service = MagicMock()
        mock_service.delete_old_data = AsyncMock()

        with patch("app.jobs.maintenance.MaintenanceService", return_value=mock_service):
            register(settings, injector)

        # Verify scheduler.add_job was called
        scheduler.add_job.assert_called_once()
        call_kwargs = scheduler.add_job.call_args[1]
        assert call_kwargs["id"] == "delete_old_data"
        assert call_kwargs["trigger"] == "cron"
        assert call_kwargs["hour"] == "0"
        assert call_kwargs["minute"] == "10"
        assert call_kwargs["second"] == "0"

    def test_register_gets_scheduler_from_injector(self):
        """Test that register gets AsyncIOScheduler from injector."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()
        injector.get.return_value = scheduler

        mock_service = MagicMock()
        mock_service.delete_old_data = AsyncMock()

        with patch("app.jobs.maintenance.MaintenanceService", return_value=mock_service):
            register(settings, injector)

        injector.get.assert_called()

    def test_delete_old_data_job_calls_service(self):
        """Test that delete_old_data job calls MaintenanceService.delete_old_data."""
        settings = MagicMock()
        settings.STATISTIC_KEEP_DAYS = 3
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.delete_old_data = AsyncMock()

        # Make injector.get return the mock service when MaintenanceService is requested
        def get_side_effect(cls):
            if cls is MaintenanceService:
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
        mock_service.delete_old_data.assert_called_once_with(3)