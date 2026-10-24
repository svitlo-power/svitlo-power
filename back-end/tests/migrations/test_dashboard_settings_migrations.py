import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models.dashboard_config import DashboardConfig, OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting
from shared.services.dashboard.config_settings import DASHBOARD_SETTING_KEYS


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def load_migration(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, MIGRATIONS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_dashboard_setting_migration_definitions():
    migration = load_migration(
        "20261024160000_seed_dashboard_settings.py",
        "seed_dashboard_settings_migration",
    )

    settings = migration.dashboard_settings()

    assert tuple(setting.key for setting in settings) == DASHBOARD_SETTING_KEYS
    assert settings[0].setting_type == "localizable_text"
    assert settings[0].default_value.root == {
        "en": "Dashboard",
        "uk": "Панель керування",
    }
    assert all(setting.category == "dashboard" for setting in settings)


@pytest.mark.asyncio
async def test_seed_dashboard_settings_inserts_only_missing_settings():
    migration = load_migration(
        "20261024160000_seed_dashboard_settings.py",
        "seed_dashboard_settings_insert_migration",
    )
    insert = AsyncMock()

    with patch.object(SystemSetting, "find_one", new_callable=AsyncMock, return_value=None), \
         patch.object(SystemSetting, "insert", new=insert):
        await migration.Forward.seed_dashboard_settings.function(
            migration.Forward(),
            "session",
        )

    assert insert.await_count == len(DASHBOARD_SETTING_KEYS)


@pytest.mark.asyncio
async def test_dashboard_config_migration_moves_values_and_drops_collection():
    migration = load_migration(
        "20261024170000_migrate_dashboard_config_to_settings.py",
        "migrate_dashboard_config_to_settings",
    )
    config = DashboardConfig(
        title=LocalizableValue({"en": "My dashboard", "uk": "Моя панель"}),
        outages_schedule=OutagesScheduleConfig(
            enable=True,
            region="Kyiv",
            dso="Yasno",
            queue="1.2",
        ),
    )
    stored_settings = {}
    for key in DASHBOARD_SETTING_KEYS:
        stored_settings[key] = MagicMock(value=None, save=AsyncMock())

    collection = MagicMock()
    collection.drop = AsyncMock()

    with patch.object(DashboardConfig, "find_one", new_callable=AsyncMock, return_value=config), \
         patch.object(
             SystemSetting,
             "find_one",
             new_callable=AsyncMock,
             side_effect=list(stored_settings.values()),
         ), \
         patch.object(DashboardConfig, "get_pymongo_collection", return_value=collection):
        await migration.Forward.move_dashboard_config_to_settings.function(
            migration.Forward(),
            "session",
        )

    assert stored_settings[migration.DASHBOARD_TITLE_SETTING_KEY].value == config.title
    assert stored_settings[migration.DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY].value is True
    assert stored_settings[migration.DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY].value == "Kyiv"
    assert stored_settings[migration.DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY].value == "Yasno"
    assert stored_settings[migration.DASHBOARD_OUTAGES_SCHEDULE_QUEUE_SETTING_KEY].value == "1.2"
    for setting in stored_settings.values():
        setting.save.assert_awaited_once_with(session="session")
    collection.drop.assert_awaited_once_with(session="session")


@pytest.mark.asyncio
async def test_dashboard_config_migration_refuses_to_drop_collection_if_setting_is_missing():
    migration = load_migration(
        "20261024170000_migrate_dashboard_config_to_settings.py",
        "migrate_dashboard_config_missing_setting",
    )
    config = DashboardConfig(
        title=LocalizableValue({"en": "Dashboard"}),
        outages_schedule=None,
    )
    collection = MagicMock()
    collection.drop = AsyncMock()

    with patch.object(DashboardConfig, "find_one", new_callable=AsyncMock, return_value=config), \
         patch.object(SystemSetting, "find_one", new_callable=AsyncMock, return_value=None), \
         patch.object(DashboardConfig, "get_pymongo_collection", return_value=collection):
        with pytest.raises(RuntimeError, match="Required dashboard setting"):
            await migration.Forward.move_dashboard_config_to_settings.function(
                migration.Forward(),
                "session",
            )

    collection.drop.assert_not_awaited()


@pytest.mark.asyncio
async def test_dashboard_config_migration_backward_restores_document_from_settings():
    migration = load_migration(
        "20261024170000_migrate_dashboard_config_to_settings.py",
        "restore_dashboard_config_from_settings",
    )
    setting_values = [
        LocalizableValue({"en": "Restored", "uk": "Відновлено"}),
        True,
        "Kyiv",
        "Yasno",
        "1.3",
    ]
    settings = [
        MagicMock(value=value, default_value=None)
        for value in setting_values
    ]
    restored_configs = []

    async def capture_insert(config, session):
        restored_configs.append(config)

    with patch.object(SystemSetting, "find_one", new_callable=AsyncMock, side_effect=settings), \
         patch.object(DashboardConfig, "insert", new=capture_insert):
        await migration.Backward.restore_dashboard_config_collection.function(
            migration.Backward(),
            "session",
        )

    assert len(restored_configs) == 1
    assert restored_configs[0].title == setting_values[0]
    assert restored_configs[0].outages_schedule == OutagesScheduleConfig(
        enable=True,
        region="Kyiv",
        dso="Yasno",
        queue="1.3",
    )
