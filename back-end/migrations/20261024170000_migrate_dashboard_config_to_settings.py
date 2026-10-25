from beanie import free_fall_migration

from shared.models.dashboard_config import DashboardConfig, OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting
from shared.services.dashboard.config_settings import (
    DASHBOARD_TITLE_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_QUEUE_SETTING_KEY,
)


async def get_setting_value(key: str, session):
    setting = await SystemSetting.find_one({"key": key}, session=session)
    if setting is None:
        raise RuntimeError(f"Required dashboard setting '{key}' is missing")
    return setting.value if setting.value is not None else setting.default_value


class Forward:
    @free_fall_migration(document_models=[DashboardConfig, SystemSetting])
    async def move_dashboard_config_to_settings(self, session):
        config = await DashboardConfig.find_one(session=session)
        if config:
            schedule = config.outages_schedule
            values = {
                DASHBOARD_TITLE_SETTING_KEY: config.title,
                DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY: bool(
                    schedule and schedule.enable
                ),
                DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY: (
                    schedule.region_id if schedule and schedule.region_id else ""
                ),
                DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY: (
                    schedule.dso_id if schedule and schedule.dso_id else ""
                ),
                DASHBOARD_OUTAGES_SCHEDULE_QUEUE_SETTING_KEY: (
                    schedule.queue if schedule and schedule.queue else ""
                ),
            }
            settings = {}
            for key in values:
                setting = await SystemSetting.find_one(
                    {"key": key},
                    session=session,
                )
                if setting is None:
                    raise RuntimeError(f"Required dashboard setting '{key}' is missing")
                settings[key] = setting

            for key, value in values.items():
                settings[key].value = value
                await settings[key].save(session=session)

        await DashboardConfig.get_pymongo_collection().drop(session=session)


class Backward:
    @free_fall_migration(document_models=[DashboardConfig, SystemSetting])
    async def restore_dashboard_config_collection(self, session):
        title = await get_setting_value(DASHBOARD_TITLE_SETTING_KEY, session)
        enabled = await get_setting_value(DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY, session)
        region = await get_setting_value(DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY, session)
        dso = await get_setting_value(DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY, session)
        queue = await get_setting_value(DASHBOARD_OUTAGES_SCHEDULE_QUEUE_SETTING_KEY, session)
        await DashboardConfig(
            title=title if isinstance(title, LocalizableValue) else LocalizableValue.model_validate(title),
            outages_schedule=OutagesScheduleConfig(
                enable=bool(enabled),
                region_id=region or None,
                dso_id=dso or None,
                queue=queue or None,
            ),
        ).insert(session=session)
