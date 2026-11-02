"""Tests for ShadowCompareMiddleware."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.middleware.shadow_compare import ShadowCompareMiddleware


@pytest.fixture
def mock_snapshot_client():
    client = MagicMock()
    client.get_snapshot.return_value = None
    return client


@pytest.fixture
def mock_legacy_service():
    service = AsyncMock()
    service.get_buildings_with_summary.return_value = []
    return service


@pytest.fixture
def shadow_compare(mock_snapshot_client, mock_legacy_service):
    return ShadowCompareMiddleware(
        snapshot_client=mock_snapshot_client,
        legacy_get_buildings_with_summary=mock_legacy_service.get_buildings_with_summary,
    )


class TestShadowCompareMiddlewareInit:
    def test_init_stores_dependencies(self, mock_snapshot_client, mock_legacy_service):
        middleware = ShadowCompareMiddleware(
            snapshot_client=mock_snapshot_client,
            legacy_get_buildings_with_summary=mock_legacy_service.get_buildings_with_summary,
        )
        assert middleware._snapshot_client == mock_snapshot_client
        assert middleware._task is None

    def test_default_interval(self, mock_snapshot_client, mock_legacy_service):
        middleware = ShadowCompareMiddleware(
            snapshot_client=mock_snapshot_client,
            legacy_get_buildings_with_summary=mock_legacy_service.get_buildings_with_summary,
        )
        assert middleware._interval_seconds == 60

    def test_default_sample_rate(self, mock_snapshot_client, mock_legacy_service):
        middleware = ShadowCompareMiddleware(
            snapshot_client=mock_snapshot_client,
            legacy_get_buildings_with_summary=mock_legacy_service.get_buildings_with_summary,
        )
        assert middleware._sample_rate == 0.01


class TestShadowCompareMiddlewareStartStop:
    @pytest.mark.asyncio
    async def test_start_creates_task(self, shadow_compare):
        await shadow_compare.start()
        assert shadow_compare._task is not None
        await shadow_compare.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self, shadow_compare):
        await shadow_compare.start()
        task = shadow_compare._task
        await shadow_compare.stop()
        assert task.cancelled()


class TestShadowCompareSample:
    def test_sample_skips_when_above_rate(self, shadow_compare, mock_snapshot_client):
        with patch('app.middleware.shadow_compare.random.random', return_value=0.5):
            # 0.5 > 0.01, should skip
            asyncio.run(shadow_compare.shadow_compare_sample({}))
            mock_snapshot_client.get_snapshot.assert_not_called()

    def test_sample_runs_when_below_rate(self, shadow_compare, mock_snapshot_client):
        snapshot = MagicMock()
        mock_snapshot_client.get_snapshot.return_value = snapshot
        with patch('app.middleware.shadow_compare.random.random', return_value=0.001):
            # 0.001 < 0.01, should run
            asyncio.run(shadow_compare.shadow_compare_sample({}))
            mock_snapshot_client.get_snapshot.assert_called_once()

    def test_sample_skips_when_no_snapshot(self, shadow_compare, mock_snapshot_client):
        mock_snapshot_client.get_snapshot.return_value = None
        with patch('app.middleware.shadow_compare.random.random', return_value=0.001):
            asyncio.run(shadow_compare.shadow_compare_sample({}))
            # Should not raise, just skip


class TestShadowCompareCompareOnce:
    @pytest.mark.asyncio
    async def test_compare_once_compares_buildings_lists(
        self, shadow_compare, mock_snapshot_client, mock_legacy_service
    ):
        """_compare_once should compare legacy buildings list vs snapshot.buildings list."""
        legacy_buildings = [
            {"id": "b1", "name": {"en": "B1"}, "color": "red", "order": 1}
        ]
        mock_legacy_service.get_buildings_with_summary.return_value = legacy_buildings

        snapshot = MagicMock()
        snapshot.buildings = [
            {"id": "b1", "name": {"en": "B1"}, "color": "red", "order": 1}
        ]
        mock_snapshot_client.get_snapshot.return_value = snapshot

        with patch(
            "app.middleware.shadow_compare.DeepDiff", return_value={}
        ) as mock_deepdiff:
            await shadow_compare._compare_once()

        # DeepDiff should be called with legacy list and snapshot.buildings list
        mock_deepdiff.assert_called_once()
        args = mock_deepdiff.call_args[0]
        assert args[0] == legacy_buildings
        assert args[1] == snapshot.buildings

    @pytest.mark.asyncio
    async def test_compare_once_skips_when_no_snapshot(
        self, shadow_compare, mock_snapshot_client, mock_legacy_service
    ):
        mock_snapshot_client.get_snapshot.return_value = None

        with patch(
            "app.middleware.shadow_compare.DeepDiff"
        ) as mock_deepdiff:
            await shadow_compare._compare_once()

        mock_deepdiff.assert_not_called()
