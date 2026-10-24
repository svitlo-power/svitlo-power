import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.models.dashboard_config import DashboardConfig, OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue
from shared.models.outages_schedule import OutagesSchedule


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def load_migration(filename: str, module_name: str):
    spec = importlib.util.spec_from_file_location(
        module_name,
        MIGRATIONS_DIR / filename,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("enabled", "queue", "expected"),
    [
        (
            True,
            "1.1",
            OutagesScheduleConfig(
                enable=True,
                region="Kyiv",
                dso="Yasno",
                queue="1.1",
            ),
        ),
        (
            False,
            None,
            OutagesScheduleConfig(
                enable=False,
                region=None,
                dso=None,
                queue=None,
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_nested_schedule_migration(enabled, queue, expected):
    migration = load_migration(
        "20261024140000_nested_outages_schedule.py",
        "nested_outages_schedule_migration",
    )
    old_config = migration.OldDashboardConfig(
        title=LocalizableValue({"en": "Dashboard"}),
        enable_outages_schedule=enabled,
        outages_schedule_queue=queue,
    )
    new_config = DashboardConfig.model_construct()

    await migration.Forward.nest_outages_schedule.function(
        migration.Forward(),
        old_config,
        new_config,
    )

    assert new_config.title == old_config.title
    assert new_config.outages_schedule == expected


@pytest.mark.asyncio
async def test_nested_schedule_migration_backward_maps_nested_values():
    migration = load_migration(
        "20261024140000_nested_outages_schedule.py",
        "nested_outages_schedule_backward_migration",
    )
    new_config = DashboardConfig.model_construct(
        title=LocalizableValue({"en": "Dashboard"}),
        outages_schedule=OutagesScheduleConfig(
            enable=True,
            region="Kyiv",
            dso="Yasno",
            queue="1.2",
        ),
    )
    old_config = migration.OldDashboardConfig.model_construct()

    await migration.Backward.flatten_outages_schedule.function(
        migration.Backward(),
        new_config,
        old_config,
    )

    assert old_config.title == new_config.title
    assert old_config.enable_outages_schedule is True
    assert old_config.outages_schedule_queue == "1.2"


@pytest.mark.asyncio
async def test_nested_schedule_backward_migration_handles_missing_schedule():
    migration = load_migration(
        "20261024140000_nested_outages_schedule.py",
        "nested_outages_schedule_empty_backward_migration",
    )
    new_config = DashboardConfig.model_construct(
        title=LocalizableValue({"en": "Dashboard"}),
        outages_schedule=None,
    )
    old_config = migration.OldDashboardConfig.model_construct()

    await migration.Backward.flatten_outages_schedule.function(
        migration.Backward(),
        new_config,
        old_config,
    )

    assert old_config.enable_outages_schedule is False
    assert old_config.outages_schedule_queue is None


@pytest.mark.asyncio
async def test_drop_collection_migration_and_rollback():
    migration = load_migration(
        "20261024150000_drop_outages_schedule_collection.py",
        "drop_outages_schedule_collection_migration",
    )
    collection = MagicMock()
    collection.drop = AsyncMock()
    collection.create_index = AsyncMock()

    with patch.object(OutagesSchedule, "get_pymongo_collection", return_value=collection):
        await migration.Forward.drop_outages_schedule_collection.function(
            migration.Forward(),
            "session",
        )
        collection.drop.assert_awaited_once_with(session="session")

        await migration.Backward.recreate_outages_schedule_collection.function(
            migration.Backward(),
            "session",
        )
        collection.create_index.assert_awaited_once_with("queue", session="session")
