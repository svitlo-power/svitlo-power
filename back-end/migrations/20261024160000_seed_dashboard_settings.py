from beanie import free_fall_migration

from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting

DASHBOARD_SETTING_KEYS = (
    "dashboard_title",
    "dashboard_outages_schedule_enabled",
    "dashboard_outages_schedule_region",
    "dashboard_outages_schedule_dso",
    "dashboard_outages_schedule_queue",
)


def dashboard_settings():
    return [
        SystemSetting(
            key="dashboard_title",
            label="Dashboard title",
            description="Localized title shown on the dashboard",
            setting_type="localizable_text",
            default_value=LocalizableValue({"en": "Dashboard", "uk": "Панель керування"}),
            value=None,
            category="dashboard",
        ),
        SystemSetting(
            key="dashboard_outages_schedule_enabled",
            label="Enable outage schedule",
            description="Show outage schedules on the dashboard",
            setting_type="boolean",
            default_value=False,
            value=None,
            category="dashboard",
        ),
        SystemSetting(
            key="dashboard_outages_schedule_region",
            label="Outage schedule region",
            description="Region used to fetch outage schedules",
            setting_type="text",
            default_value="",
            value=None,
            category="dashboard",
        ),
        SystemSetting(
            key="dashboard_outages_schedule_dso",
            label="Outage schedule provider",
            description="Distribution system operator used to fetch outage schedules",
            setting_type="text",
            default_value="",
            value=None,
            category="dashboard",
        ),
        SystemSetting(
            key="dashboard_outages_schedule_queue",
            label="Outage schedule queue",
            description="Queue configured for the outage schedule",
            setting_type="text",
            default_value="",
            value=None,
            category="dashboard",
        ),
    ]


class Forward:
    @free_fall_migration(document_models=[SystemSetting])
    async def seed_dashboard_settings(self, session):
        for setting in dashboard_settings():
            existing = await SystemSetting.find_one(
                {"key": setting.key},
                session=session,
            )
            if existing is None:
                await setting.insert(session=session)


class Backward:
    @free_fall_migration(document_models=[SystemSetting])
    async def remove_dashboard_settings(self, session):
        for key in DASHBOARD_SETTING_KEYS:
            setting = await SystemSetting.find_one(
                {"key": key},
                session=session,
            )
            if setting:
                await setting.delete(session=session)
