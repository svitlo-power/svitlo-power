from beanie import free_fall_migration
from datetime import datetime, timezone

from shared.models.system_setting import SystemSetting


REGION_SETTING_KEY = "dashboard_outages_schedule_region"
DSO_SETTING_KEY = "dashboard_outages_schedule_dso"
QUEUE_SETTING_KEY = "dashboard_outages_schedule_queue"


class Forward:
    @free_fall_migration(document_models=[SystemSetting])
    async def use_ids_for_schedule_location(self, session):
        for key in (REGION_SETTING_KEY, DSO_SETTING_KEY):
            setting = await SystemSetting.find_one({"key": key}, session=session)
            if setting is None:
                raise RuntimeError(f"Required dashboard setting '{key}' is missing")
            # Legacy names remain readable until the scheduler resolves them to IDs.
            setting.setting_type = "number"
            setting.default_value = 0
            if isinstance(setting.value, str) and setting.value.isdecimal():
                setting.value = int(setting.value)
            setting.editable = False
            setting.updated_at = datetime.now(timezone.utc)
            await setting.save(session=session)

        setting = await SystemSetting.find_one(
            {"key": QUEUE_SETTING_KEY},
            session=session,
        )
        if setting is None:
            raise RuntimeError(f"Required dashboard setting '{QUEUE_SETTING_KEY}' is missing")
        setting.editable = False
        setting.updated_at = datetime.now(timezone.utc)
        await setting.save(session=session)


class Backward:
    @free_fall_migration(document_models=[SystemSetting])
    async def restore_editable_schedule_settings(self, session):
        settings = {
            key: await SystemSetting.find_one({"key": key}, session=session)
            for key in (REGION_SETTING_KEY, DSO_SETTING_KEY, QUEUE_SETTING_KEY)
        }
        if any(
            setting is not None and isinstance(setting.value, int)
            for key, setting in settings.items()
            if key in (REGION_SETTING_KEY, DSO_SETTING_KEY)
        ):
            raise RuntimeError(
                "Cannot downgrade ID-based outage settings without restoring "
                "the original region and provider names"
            )

        for key, setting in settings.items():
            if setting is None:
                continue
            if key in (REGION_SETTING_KEY, DSO_SETTING_KEY):
                setting.setting_type = "text"
                setting.default_value = ""
            setting.editable = True
            setting.updated_at = datetime.now(timezone.utc)
            await setting.save(session=session)
