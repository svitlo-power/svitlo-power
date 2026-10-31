from datetime import datetime
import logging
import asyncio
import aiohttp
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from injector import Injector

from app.settings import Settings
from shared.services import OutagesScheduleService
from shared.services.dashboard.config_settings import (
    DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY,
)
from shared.services.settings.service import SettingsService
from shared.services.dashboard.config_settings import (
    LEGACY_YASNO_PROVIDER_ID,
    LEGACY_YASNO_PROVIDER_NAME,
    LEGACY_YASNO_REGION_ID,
    LEGACY_YASNO_REGION_NAME,
)
from shared.features import feature_flags, FeatureFlag
from app.services.dashboard_snapshot.service import DashboardSnapshotService

logger = logging.getLogger(__name__)


def register(_: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def update_outages_schedule():
        # Only update outages schedule if admin CRUD migration is NOT enabled (legacy path)
        if not feature_flags.is_enabled(FeatureFlag.ADMIN_CRUD_PROCESSING):
            service = injector.get(OutagesScheduleService)
            settings = injector.get(SettingsService)
            enabled = await settings.get_boolean(
                DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY,
                False,
            )
            region_setting = await settings.get_value(DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY)
            dso_setting = await settings.get_value(DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY)
            if not region_setting or not dso_setting:
                if enabled:
                    logger.warning(
                        "Outage schedule is enabled without a configured region and provider"
                    )
                return
            if not enabled and _as_id(region_setting) and _as_id(dso_setting):
                return

            try:
                regions = await service.fetch_regions()
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
                logger.warning("Unable to discover outage schedule region/provider: %s", error)
                return
            region_id = _as_id(region_setting)
            region = (
                next((item for item in regions if item["id"] == region_id), None)
                if region_id is not None
                else next((item for item in regions if item["value"] == region_setting), None)
            )
            if region is None and region_setting == LEGACY_YASNO_REGION_NAME:
                region = next(
                    (item for item in regions if item["id"] == LEGACY_YASNO_REGION_ID),
                    None,
                )
            if region is None:
                logger.warning("Configured outage region %s is no longer available", region_setting)
                return
            provider_id = _as_id(dso_setting)
            provider = (
                next((item for item in region["dsos"] if item["id"] == provider_id), None)
                if provider_id is not None
                else next((item for item in region["dsos"] if item["name"] == dso_setting), None)
            )
            if (
                provider is None
                and dso_setting == LEGACY_YASNO_PROVIDER_NAME
                and region["id"] == LEGACY_YASNO_REGION_ID
            ):
                provider = next(
                    (item for item in region["dsos"] if item["id"] == LEGACY_YASNO_PROVIDER_ID),
                    None,
                )
            if provider is None:
                logger.warning(
                    "Configured outage provider %s is unavailable in %s",
                    dso_setting,
                    region["value"],
                )
                return
            if not isinstance(region_setting, int):
                region_setting = await settings.set_value(
                    DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY,
                    region["id"],
                )
                if region_setting is not None:
                    region_setting.setting_type = "number"
                    await region_setting.save()
            if not isinstance(dso_setting, int):
                dso_setting = await settings.set_value(
                    DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY,
                    provider["id"],
                )
                if dso_setting is not None:
                    dso_setting.setting_type = "number"
                    await dso_setting.save()
            if not enabled:
                return
            await service.update(region["id"], provider["id"])
            snapshot_service = injector.get(DashboardSnapshotService)
            await snapshot_service.refresh_and_publish()

    scheduler.add_job(
        id            = 'update_outages_schedule',
        func          = update_outages_schedule,
        trigger       = 'interval',
        minutes       = 5,
        next_run_time = datetime.now(),
        max_instances = 1
    )


def _as_id(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str) and value.isdecimal() and int(value) > 0:
        return int(value)
    return None
