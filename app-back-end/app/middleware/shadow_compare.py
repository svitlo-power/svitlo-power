"""Shadow comparison middleware for app-back-end.

Compares legacy dashboard calculations against Redis snapshots in the background
(off the hot request path) and emits parity mismatch metrics.
"""

import asyncio
import logging
import random
from typing import Any, Callable, Optional

from deepdiff import DeepDiff

from app.clients.dashboard_snapshot_client import DashboardSnapshotClient
from shared.features import feature_flags, FeatureFlag
from shared.metrics import DASHBOARD_PARITY_MISMATCHES

logger = logging.getLogger(__name__)

SHADOW_COMPARE_INTERVAL_SECONDS = 60
SHADOW_SAMPLE_RATE = 0.01  # 1% of requests


class ShadowCompareMiddleware:
    """Background shadow comparison of legacy vs Redis snapshot data.

    Runs periodic full comparisons and optional per-request sampling.
    Does NOT run deep-diff on the hot request path.
    """

    def __init__(
        self,
        snapshot_client: DashboardSnapshotClient,
        legacy_get_buildings_with_summary: Callable,
        *,
        interval_seconds: int = SHADOW_COMPARE_INTERVAL_SECONDS,
        sample_rate: float = SHADOW_SAMPLE_RATE,
    ) -> None:
        self._snapshot_client = snapshot_client
        self._legacy_get_buildings_with_summary = legacy_get_buildings_with_summary
        self._interval_seconds = interval_seconds
        self._sample_rate = sample_rate
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """Start the background shadow comparison task."""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._shadow_compare_task())

    async def stop(self) -> None:
        """Stop the background shadow comparison task."""
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _shadow_compare_task(self) -> None:
        """Periodic background comparison, not per-request."""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._interval_seconds)
            except asyncio.CancelledError:
                break
            if self._stop_event.is_set():
                break
            try:
                await self._compare_once()
            except Exception as e:
                logger.error("Shadow compare failed: %s", e)

    async def _compare_once(self) -> None:
        """Perform a single legacy vs Redis snapshot comparison.

        Compares the buildings list from the legacy service against the
        buildings list from the Redis snapshot (same shape).
        """
        legacy = await self._legacy_get_buildings_with_summary()
        redis_snapshot = self._snapshot_client.get_snapshot()
        if redis_snapshot is None:
            return

        legacy_data = self._serialize_legacy(legacy)
        redis_data = self._serialize_redis(redis_snapshot.buildings)

        diff = DeepDiff(legacy_data, redis_data, ignore_order=True)
        if diff:
            for path in diff.keys():
                DASHBOARD_PARITY_MISMATCHES.labels(field_path=str(path)).inc()
            logger.warning(
                "Shadow parity mismatch: %s",
                diff,
            )

    async def shadow_compare_sample(
        self,
        legacy_response: Any,
    ) -> None:
        """Optionally compare a per-request legacy response against Redis snapshot.

        Called with 1% probability; comparison happens in background and does
        not block the response.
        """
        if random.random() >= self._sample_rate:
            return
        redis_snapshot = self._snapshot_client.get_snapshot()
        if redis_snapshot is None:
            return

        asyncio.create_task(self._compare_response(legacy_response, redis_snapshot))

    async def _compare_response(self, legacy_response: Any, redis_snapshot) -> None:
        """Compare a single legacy response against Redis snapshot in background."""
        try:
            legacy_data = self._serialize_legacy_response(legacy_response)
            redis_data = self._serialize_redis(redis_snapshot)
            diff = DeepDiff(legacy_data, redis_data, ignore_order=True)
            if diff:
                for path in diff.keys():
                    DASHBOARD_PARITY_MISMATCHES.labels(field_path=str(path)).inc()
                logger.warning("Shadow sample parity mismatch: %s", diff)
        except Exception as e:
            logger.error("Shadow sample compare failed: %s", e)

    @staticmethod
    def _serialize_legacy(legacy: Any) -> Any:
        """Serialize legacy service response to plain dict for comparison."""
        if legacy is None:
            return None
        if isinstance(legacy, list):
            return [ShadowCompareMiddleware._serialize_legacy(item) for item in legacy]
        if hasattr(legacy, "model_dump"):
            return legacy.model_dump()
        if hasattr(legacy, "dict"):
            return legacy.dict()
        return legacy

    @staticmethod
    def _serialize_legacy_response(response: Any) -> Any:
        """Serialize a per-request legacy response (e.g. FastAPI response body)."""
        if response is None:
            return None
        if isinstance(response, list):
            return [
                ShadowCompareMiddleware._serialize_legacy_response(item)
                for item in response
            ]
        if hasattr(response, "body"):
            import json

            try:
                return json.loads(response.body)
            except Exception:
                return str(response.body)
        if hasattr(response, "model_dump"):
            return response.model_dump()
        if hasattr(response, "dict"):
            return response.dict()
        return response

    @staticmethod
    def _serialize_redis(snapshot) -> Any:
        """Serialize Redis snapshot to plain dict for comparison."""
        if snapshot is None:
            return None
        if isinstance(snapshot, list):
            return [ShadowCompareMiddleware._serialize_redis(item) for item in snapshot]
        if hasattr(snapshot, "model_dump"):
            return snapshot.model_dump()
        if hasattr(snapshot, "dict"):
            return snapshot.dict()
        return snapshot
