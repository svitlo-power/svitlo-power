from beanie import free_fall_migration

from shared.models.system_setting import SystemSetting


class Forward:
    @free_fall_migration(document_models=[SystemSetting])
    async def seed_default_settings(self, session):
        defaults = [
            SystemSetting(
                key="discharge_target_soc",
                label="Discharge Target SOC",
                description="Battery % to stop discharging",
                setting_type="number",
                default_value=10,
                value=10,
                validation={"min": 0, "max": 100},
                category="power_estimation",
            ),
            SystemSetting(
                key="charge_target_soc",
                label="Charge Target SOC",
                description="Battery % to stop charging",
                setting_type="number",
                default_value=97,
                value=97,
                validation={"min": 0, "max": 100},
                category="power_estimation",
            ),
            SystemSetting(
                key="estimate_discharge_period_minutes",
                label="Discharge time average consumption period",
                description="Minutes to take the average consumption for when computing the discharge time",
                setting_type="number",
                default_value=2880,
                value=2880,
                validation={"min": 20, "max": 7200},
                category="power_estimation",
            )
        ]
        
        for setting in defaults:
            existing = await SystemSetting.find_one(SystemSetting.key == setting.key, session=session)
            if not existing:
                await setting.insert(session=session)


class Backward:
    @free_fall_migration(document_models=[SystemSetting])
    async def remove_default_settings(self, session):
        keys_to_remove = [
            "discharge_target_soc",
            "charge_target_soc",
            "estimate_discharge_period_minutes",
        ]
        
        for key in keys_to_remove:
            setting = await SystemSetting.find_one(SystemSetting.key == key, session=session)
            if setting:
                await setting.delete(session=session)