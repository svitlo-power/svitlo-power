"""Tests for the Phase 5 snapshot refresh trigger publisher."""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.dashboard_snapshot.service import DashboardSnapshotService
from shared.features import feature_flags, FeatureFlag
from shared.services.dashboard_snapshot.triggers import SNAPSHOT_REFRESH_CHANNEL


class _MockSettings:
    REDIS_URI = "redis://localhost:6379"


def _service(publish=None):
    service = DashboardSnapshotService(
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        _MockSettings(),
    )
    # `AsyncMock(spec=Redis)` exposes `publish` as a plain MagicMock, so the
    # coroutine has to be supplied explicitly.
    redis = MagicMock()
    redis.publish = publish or AsyncMock()
    service._redis = redis
    return service, redis


@pytest.fixture(autouse=True)
def reset_cutover_flag():
    previous = feature_flags.get_config(FeatureFlag.PROCESSING_CUTOVER)
    yield
    feature_flags.set_enabled(
        FeatureFlag.PROCESSING_CUTOVER,
        bool(previous and previous.enabled),
    )


class TestNotifyDataChanged:
    @pytest.mark.asyncio
    async def test_publishes_a_hint_on_the_versioned_channel(self):
        feature_flags.set_enabled(FeatureFlag.PROCESSING_CUTOVER, True)
        service, redis = _service()

        await service.notify_data_changed("buildings-change")

        redis.publish.assert_awaited_once()
        channel, payload = redis.publish.await_args.args
        assert channel == SNAPSHOT_REFRESH_CHANNEL
        assert json.loads(payload) == {
            "reason": "buildings-change",
            "source": "back-end",
        }

    @pytest.mark.asyncio
    async def test_changed_sections_are_carried_as_a_hint(self):
        feature_flags.set_enabled(FeatureFlag.PROCESSING_CUTOVER, True)
        service, redis = _service()

        await service.notify_data_changed(
            "config-change", changed_sections=["config"]
        )

        payload = json.loads(redis.publish.await_args.args[1])
        assert payload["changedSections"] == ["config"]

    @pytest.mark.asyncio
    async def test_inert_until_the_cutover_flag_is_on(self):
        feature_flags.set_enabled(FeatureFlag.PROCESSING_CUTOVER, False)
        service, redis = _service()

        await service.notify_data_changed("buildings-change")

        # While the legacy producer still publishes there is nothing to notify,
        # and after a rollback the re-enabled publisher must not be fed hints.
        redis.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_a_redis_failure_never_fails_the_domain_write(self):
        feature_flags.set_enabled(FeatureFlag.PROCESSING_CUTOVER, True)
        # Fire and forget: a Processing or Redis outage must not surface as a
        # failed admin mutation.
        service, _ = _service(
            publish=AsyncMock(side_effect=ConnectionError("redis down"))
        )

        await service.notify_data_changed("station-change")

    @pytest.mark.asyncio
    async def test_trigger_is_independent_of_the_publish_flag(self):
        feature_flags.set_enabled(FeatureFlag.PROCESSING_CUTOVER, True)
        feature_flags.set_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH, False)
        service, _ = _service()

        # The cutover turns the legacy publisher off and the trigger on; the two
        # flags must be readable independently for the rollback drill.
        assert service.is_refresh_trigger_enabled is True
        assert service.is_publish_enabled is False