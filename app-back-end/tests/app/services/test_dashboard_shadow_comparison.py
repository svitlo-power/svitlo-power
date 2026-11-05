import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.dashboard_shadow_comparison import (
    DashboardShadowComparison,
    _find_differences,
)


@pytest.mark.asyncio
async def test_sample_comparison_runs_off_the_calling_task():
    completed = asyncio.Event()
    legacy_loader = AsyncMock(side_effect=lambda: completed.set() or {"value": 1})
    comparison = DashboardShadowComparison(
        MagicMock(),
        MagicMock(),
        sample_rate=1,
    )

    assert comparison.sample("endpoint", legacy_loader, lambda: {"value": 1}) is None
    legacy_loader.assert_not_awaited()

    await asyncio.wait_for(completed.wait(), timeout=1)
    await asyncio.sleep(0)
    legacy_loader.assert_awaited_once()
    await comparison.stop()


@pytest.mark.asyncio
async def test_periodic_comparison_runs_against_the_current_snapshot():
    compared = asyncio.Event()
    dashboard = MagicMock()

    async def load_legacy():
        compared.set()
        return []

    dashboard.get_buildings_with_summary = AsyncMock(side_effect=load_legacy)
    snapshot_client = MagicMock()
    snapshot_client.get_snapshot.return_value = MagicMock(buildings=[])
    comparison = DashboardShadowComparison(
        dashboard,
        snapshot_client,
        interval_seconds=0.01,
    )

    await comparison.start()
    try:
        await asyncio.wait_for(compared.wait(), timeout=1)
        dashboard.get_buildings_with_summary.assert_awaited_once()
    finally:
        await comparison.stop()


def test_difference_paths_are_field_level_and_bounded():
    assert _find_differences(
        [{"batteryPercent": 50, "name": "a"}],
        [{"batteryPercent": 49, "name": "a"}],
    ) == ["$[].batteryPercent"]
