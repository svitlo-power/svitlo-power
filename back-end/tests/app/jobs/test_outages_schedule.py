"""Tests for app/jobs/outages_schedule.py."""
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock

from app.jobs.outages_schedule import register
from shared.services import OutagesScheduleService
from shared.models.dashboard_config import DashboardConfig, OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue


class TestRegister:
    @staticmethod
    def _job_for_service(mock_service):
        injector = MagicMock()
        scheduler = MagicMock()
        injector.get.side_effect = lambda cls: (
            mock_service if cls is OutagesScheduleService else scheduler
        )
        register(MagicMock(), injector)
        return scheduler.add_job.call_args.kwargs["func"]

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
        mock_service.fetch_regions = AsyncMock(return_value=[{
            "id": 25,
            "value": "Київ",
            "dsos": [{"id": 902, "name": "ДТЕК Київські електромережі"}],
        }])

        def get_side_effect(cls):
            if cls is OutagesScheduleService:
                return mock_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the job function and execute it
        call_kwargs = scheduler.add_job.call_args[1]
        job_func = call_kwargs["func"]

        config = DashboardConfig(
            title=LocalizableValue({"en": "Dashboard"}),
            outages_schedule=OutagesScheduleConfig(
                enable=True,
                region="Kyiv",
                dso="Yasno",
                queue="1.1",
            ),
        )
        with patch(
            "app.jobs.outages_schedule.DashboardConfig.find_one",
            new_callable=AsyncMock,
            return_value=config,
        ):
            asyncio.run(job_func())

        mock_service.fetch_regions.assert_awaited_once()
        mock_service.update.assert_called_once_with(25, 902)

    def test_update_outages_schedule_job_skips_missing_or_incomplete_config(self):
        service = MagicMock()
        service.fetch_regions = AsyncMock()
        service.update = AsyncMock()
        job = self._job_for_service(service)

        configs = [
            None,
            DashboardConfig(
                title=LocalizableValue({"en": "Dashboard"}),
                outages_schedule=None,
            ),
            DashboardConfig(
                title=LocalizableValue({"en": "Dashboard"}),
                outages_schedule=OutagesScheduleConfig(enable=False),
            ),
            SimpleNamespace(outages_schedule=SimpleNamespace(
                enable=True,
                region=None,
                dso=None,
            )),
        ]

        for config in configs:
            with patch(
                "app.jobs.outages_schedule.DashboardConfig.find_one",
                new_callable=AsyncMock,
                return_value=config,
            ):
                asyncio.run(job())

        service.fetch_regions.assert_not_awaited()
        service.update.assert_not_awaited()

    def test_update_outages_schedule_job_skips_unknown_region_or_provider(self):
        service = MagicMock()
        service.update = AsyncMock()
        service.fetch_regions = AsyncMock(return_value=[{
            "id": 25,
            "value": "Київ",
            "dsos": [{"id": 902, "name": "ДТЕК Київські електромережі"}],
        }])
        job = self._job_for_service(service)

        for region, provider in [("Missing", "Any"), ("Київ", "Missing")]:
            config = DashboardConfig(
                title=LocalizableValue({"en": "Dashboard"}),
                outages_schedule=OutagesScheduleConfig(
                    enable=True,
                    region=region,
                    dso=provider,
                    queue="1.1",
                ),
            )
            with patch(
                "app.jobs.outages_schedule.DashboardConfig.find_one",
                new_callable=AsyncMock,
                return_value=config,
            ):
                asyncio.run(job())

        assert service.fetch_regions.await_count == 2
        service.update.assert_not_awaited()