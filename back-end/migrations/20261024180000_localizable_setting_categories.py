from beanie import free_fall_migration

from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting, SystemSettingCategory


CATEGORY_LABELS = {
    "power_estimation": {
        "en": "Power Estimation",
        "uk": "Оцінка потужності",
    },
    "dashboard": {
        "en": "Buildings",
        "uk": "Будівлі",
    },
}

SETTING_METADATA = {
    "discharge_target_soc": {
        "category": "power_estimation",
        "label": {
            "en": "Discharge Target SOC",
            "uk": "Цільовий рівень заряду для розрядження",
        },
        "description": {
            "en": "Battery % to stop discharging",
            "uk": "Рівень заряду батареї (%) для припинення розрядження",
        },
    },
    "charge_target_soc": {
        "category": "power_estimation",
        "label": {
            "en": "Charge Target SOC",
            "uk": "Цільовий рівень заряду для заряджання",
        },
        "description": {
            "en": "Battery % to stop charging",
            "uk": "Рівень заряду батареї (%) для припинення заряджання",
        },
    },
    "estimate_discharge_period_minutes": {
        "category": "power_estimation",
        "label": {
            "en": "Discharge time average consumption period",
            "uk": "Період середнього споживання для розрядження",
        },
        "description": {
            "en": "Minutes to take the average consumption for when computing the discharge time",
            "uk": "Кількість хвилин для усереднення споживання під час розрахунку часу розрядження",
        },
    },
    "dashboard_title": {
        "category": "dashboard",
        "label": {
            "en": "Dashboard title",
            "uk": "Назва панелі",
        },
        "description": {
            "en": "Localized title shown on the dashboard",
            "uk": "Локалізована назва, що відображається на панелі",
        },
    },
    "dashboard_outages_schedule_enabled": {
        "category": "dashboard",
        "label": {
            "en": "Enable outage schedule",
            "uk": "Увімкнути графік відключень",
        },
        "description": {
            "en": "Show outage schedules on the dashboard",
            "uk": "Показувати графіки відключень на панелі",
        },
    },
    "dashboard_outages_schedule_region": {
        "category": "dashboard",
        "label": {
            "en": "Outage schedule region",
            "uk": "Регіон графіка відключень",
        },
        "description": {
            "en": "Region used to fetch outage schedules",
            "uk": "Регіон, для якого завантажується графік відключень",
        },
    },
    "dashboard_outages_schedule_dso": {
        "category": "dashboard",
        "label": {
            "en": "Outage schedule provider",
            "uk": "Постачальник графіка відключень",
        },
        "description": {
            "en": "Distribution system operator used to fetch outage schedules",
            "uk": "Оператор системи розподілу, від якого завантажується графік відключень",
        },
    },
    "dashboard_outages_schedule_queue": {
        "category": "dashboard",
        "label": {
            "en": "Outage schedule queue",
            "uk": "Черга графіка відключень",
        },
        "description": {
            "en": "Queue configured for the outage schedule",
            "uk": "Черга, налаштована для графіка відключень",
        },
    },
}


class Forward:
    @free_fall_migration(
        document_models=[SystemSetting, SystemSettingCategory]
    )
    async def localize_setting_metadata(self, session):
        categories = {}
        for key, label in CATEGORY_LABELS.items():
            category = await SystemSettingCategory.find_one(
                {"key": key},
                session=session,
            )
            if category is None:
                category = SystemSettingCategory(
                    key=key,
                    label=LocalizableValue(label),
                )
                await category.insert(session=session)
            categories[key] = category

        settings_collection = SystemSetting.get_pymongo_collection()
        async for setting in settings_collection.find({}, session=session):
            key = setting["key"]
            metadata = SETTING_METADATA.get(key)
            if metadata is None:
                raise RuntimeError(
                    f"No localized metadata defined for system setting '{key}'"
                )
            category = categories[metadata["category"]]
            await settings_collection.update_one(
                {"_id": setting["_id"]},
                {
                    "$set": {
                        "label": metadata["label"],
                        "description": metadata["description"],
                        "category_id": category.id,
                    },
                    "$unset": {"category": ""},
                },
                session=session,
            )


class Backward:
    @free_fall_migration(
        document_models=[SystemSetting, SystemSettingCategory]
    )
    async def restore_setting_metadata(self, session):
        settings_collection = SystemSetting.get_pymongo_collection()
        async for setting in settings_collection.find({}, session=session):
            metadata = SETTING_METADATA.get(setting["key"])
            if metadata is None:
                raise RuntimeError(
                    f"No localized metadata defined for system setting "
                    f"'{setting['key']}'"
                )
            await settings_collection.update_one(
                {"_id": setting["_id"]},
                {
                    "$set": {
                        "label": metadata["label"]["en"],
                        "description": metadata["description"]["en"],
                        "category": metadata["category"],
                    },
                    "$unset": {"category_id": ""},
                },
                session=session,
            )

        categories_collection = SystemSettingCategory.get_pymongo_collection()
        await categories_collection.delete_many(
            {"key": {"$in": list(CATEGORY_LABELS)}},
            session=session,
        )
