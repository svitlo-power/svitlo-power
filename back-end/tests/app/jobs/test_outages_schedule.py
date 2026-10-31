"""Tests for app/jobs/outages_schedule.py."""
import asyncio
from unittest.mock import MagicMock, AsyncMock

import aiohttp

from app.jobs.outages_schedule import register
from app.services.dashboard_snapshot.service import DashboardSnapshotService
from shared.services import OutagesScheduleService
from shared.services.settings.service import SettingsService
from shared.features import feature_flags, FeatureFlag


class TestRegister:
    @staticmethod
    def _job_for_service(mock_service, enabled=False, region="", dso=""):
        injector = MagicMock()
        scheduler = MagicMock()
        mock_settings = MagicMock()
        mock_settings.get_boolean = AsyncMock(return_value=enabled)
        mock_settings.get_value = AsyncMock(side_effect=[region, dso])
        mock_settings.set_value = AsyncMock(return_value=None)
        mock_snapshot_service = MagicMock()
        mock_snapshot_service.refresh_and_publish = AsyncMock()
        injector.get.side_effect = lambda cls: (
            mock_service if cls is OutagesScheduleService
            else mock_settings if cls is SettingsService
            else mock_snapshot_service if cls is DashboardSnapshotService
            else scheduler
        )
        register(MagicMock(), injector)
        return scheduler.add_job.call_args.kwargs["func"], mock_settings

    def test_register_adds_update_outages_schedule_job(self):
        """Test that register adds update_outages_schedule job to scheduler."""
        settings = MagicMock()
        injector = MagicMock()
        scheduler = MagicMock()

        mock_service = MagicMock()
        mock_service.update = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.get_boolean = AsyncMock(return_value=True)
        mock_settings.get_value = AsyncMock(side_effect=["Kyiv", "Yasno"])
        mock_settings.set_value = AsyncMock(return_value=None)

        def get_side_effect(cls):
            if cls is OutagesScheduleService:
                return mock_service
            if cls is SettingsService:
                return mock_settings
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
        from shared.features import feature_flags, FeatureFlag
        feature_flags.set_enabled(FeatureFlag.ADMIN_CRUD_PROCESSING, False)

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
        mock_settings = MagicMock()
        mock_settings.get_boolean = AsyncMock(return_value=True)
        mock_settings.get_value = AsyncMock(side_effect=["Kyiv", "Yasno"])
        mock_settings.set_value = AsyncMock(return_value=None)

        mock_snapshot_service = MagicMock()
        mock_snapshot_service.refresh_and_publish = AsyncMock()

        def get_side_effect(cls):
            if cls is OutagesScheduleService:
                return mock_service
            if cls is SettingsService:
                return mock_settings
            if cls is DashboardSnapshotService:
                return mock_snapshot_service
            return scheduler

        injector.get.side_effect = get_side_effect

        register(settings, injector)

        # Get the job function and execute it
        call_kwargs = scheduler.add_job.call_args[1]
        job_func = call_kwargs["func"]

        asyncio.run(job_func())

        mock_service.fetch_regions.assert_awaited_once()
        mock_service.update.assert_called_once_with(25, 902)
        mock_settings.get_boolean.assert_awaited_once()
        assert mock_settings.get_value.await_count == 2
        assert mock_settings.set_value.await_args_list[0].args == (
            "dashboard_outages_schedule_region",
            25,
        )
        assert mock_settings.set_value.await_args_list[1].args == (
            "dashboard_outages_schedule_dso",
            902,
        )
        mock_snapshot_service.refresh_and_publish.assert_awaited_once()

    def test_update_outages_schedule_job_skips_missing_or_incomplete_config(self):
        service = MagicMock()
        service.fetch_regions = AsyncMock()
        service.update = AsyncMock()
        job, _ = self._job_for_service(service, enabled=False)
        service.fetch_regions.assert_not_awaited()
        asyncio.run(job())
        service.fetch_regions.assert_not_awaited()
        service.update.assert_not_awaited()
        job, _ = self._job_for_service(service, enabled=True, region="", dso="")
        asyncio.run(job())
        service.fetch_regions.assert_not_awaited()
        service.update.assert_not_awaited()

    def test_disabled_schedule_still_migrates_legacy_location_names(self):
        from shared.features import feature_flags, FeatureFlag
        feature_flags.set_enabled(FeatureFlag.ADMIN_CRUD_PROCESSING, False)

        service = MagicMock()
        service.fetch_regions = AsyncMock(return_value=[{
            "id": 25,
            "value": "Київ",
            "dsos": [{"id": 902, "name": "ДТЕК"}],
        }])
        service.update = AsyncMock()
        job, settings = self._job_for_service(
            service,
            enabled=False,
            region="Kyiv",
            dso="Yasno",
        )

        asyncio.run(job())

        assert settings.set_value.await_args_list[0].args == (
            "dashboard_outages_schedule_region",
            25,
        )
        assert settings.set_value.await_args_list[1].args == (
            "dashboard_outages_schedule_dso",
            902,
        )
        service.update.assert_not_awaited()

    def test_update_outages_schedule_job_skips_unknown_region_or_provider(self):
        from shared.features import feature_flags, FeatureFlag
        feature_flags.set_enabled(FeatureFlag.ADMIN_CRUD_PROCESSING, False)

        service = MagicMock()
        service.update = AsyncMock()
        service.fetch_regions = AsyncMock(return_value=[{
            "id": 25,
            "value": "Київ",
            "dsos": [{"id": 902, "name": "ДТЕК Київські електромережі"}],
        }])
        for region, provider in [("Missing", "Any"), ("Київ", "Missing")]:
            job, _ = self._job_for_service(
                service,
                enabled=True,
                region=region,
                dso=provider,
            )
            asyncio.run(job())

        assert service.fetch_regions.await_count == 2
        service.update.assert_not_awaited()

    def test_update_outages_schedule_job_logs_region_discovery_failures(self):
        from shared.features import feature_flags, FeatureFlag
        feature_flags.set_enabled(FeatureFlag.ADMIN_CRUD_PROCESSING, False)

        service = MagicMock()
        service.fetch_regions = AsyncMock(side_effect=aiohttp.ClientError("offline"))
        service.update = AsyncMock()
        job, _ = self._job_for_service(
            service,
            enabled=True,
            region="Kyiv",
            dso="Yasno",
        )

        asyncio.run(job())

        service.fetch_regions.assert_awaited_once()
        service.update.assert_not_awaited()