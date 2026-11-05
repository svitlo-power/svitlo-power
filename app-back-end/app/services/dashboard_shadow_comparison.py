"""Background parity comparisons between legacy dashboard reads and snapshots."""

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from shared.metrics import (
    APP_BACKEND_SHADOW_PARITY_LATENCY_DELTA_MS,
    APP_BACKEND_SHADOW_PARITY_MISMATCHES,
)
from shared.services.dashboard import ReadOnlyDashboardService
from shared.services.dashboard_snapshot import DashboardSnapshotClient

from app.snapshot_responses import snapshot_building_with_summary_response

logger = logging.getLogger(__name__)

LegacyLoader = Callable[[], Awaitable[Any]]
SnapshotLoader = Callable[[], Any]


class DashboardShadowComparison:
    def __init__(
        self,
        dashboard: ReadOnlyDashboardService,
        snapshot_client: DashboardSnapshotClient,
        sample_rate: float = 0.01,
        interval_seconds: int = 60,
    ):
        self._dashboard = dashboard
        self._snapshot_client = snapshot_client
        self._sample_rate = sample_rate
        self._interval_seconds = interval_seconds
        self._periodic_task: asyncio.Task | None = None
        self._sample_tasks: set[asyncio.Task] = set()

    async def start(self) -> None:
        if self._periodic_task is None:
            self._periodic_task = asyncio.create_task(self._periodic_loop())

    async def stop(self) -> None:
        tasks = list(self._sample_tasks)
        if self._periodic_task is not None:
            tasks.append(self._periodic_task)
            self._periodic_task = None
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._sample_tasks.clear()

    def sample(
        self,
        endpoint: str,
        legacy_loader: LegacyLoader,
        snapshot_loader: SnapshotLoader,
    ) -> None:
        if random.random() >= self._sample_rate:
            return
        task = asyncio.create_task(
            self._compare(endpoint, legacy_loader, snapshot_loader)
        )
        self._sample_tasks.add(task)
        task.add_done_callback(self._sample_tasks.discard)

    async def _periodic_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._interval_seconds)
                snapshot = self._snapshot_client.get_snapshot()
                if snapshot is None:
                    continue
                await self._compare(
                    "GET /api/buildings/buildings",
                    self._dashboard.get_buildings_with_summary,
                    lambda: [
                        snapshot_building_with_summary_response(building)
                        for building in snapshot.buildings
                    ],
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Periodic dashboard shadow comparison failed")

    async def _compare(
        self,
        endpoint: str,
        legacy_loader: LegacyLoader,
        snapshot_loader: SnapshotLoader,
    ) -> None:
        try:
            legacy_start = time.perf_counter()
            legacy_value = await legacy_loader()
            legacy_duration_ms = (time.perf_counter() - legacy_start) * 1000

            snapshot_start = time.perf_counter()
            snapshot_value = snapshot_loader()
            snapshot_duration_ms = (time.perf_counter() - snapshot_start) * 1000

            differences = _find_differences(
                _json_value(legacy_value),
                _json_value(snapshot_value),
            )
            APP_BACKEND_SHADOW_PARITY_LATENCY_DELTA_MS.labels(
                endpoint=endpoint
            ).observe(max(0.0, legacy_duration_ms - snapshot_duration_ms))

            for path in differences:
                metric_path = f"{endpoint}:{path}"
                APP_BACKEND_SHADOW_PARITY_MISMATCHES.labels(path=metric_path).inc()
            if differences:
                logger.warning(
                    "Dashboard snapshot parity mismatch",
                    extra={"endpoint": endpoint, "diff_paths": differences},
                )
        except Exception:
            logger.exception("Dashboard shadow comparison failed for %s", endpoint)


def _json_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _find_differences(legacy: Any, snapshot: Any, path: str = "$") -> list[str]:
    if isinstance(legacy, dict) and isinstance(snapshot, dict):
        differences = []
        for key in sorted(legacy.keys() | snapshot.keys()):
            child_path = f"{path}.{key}"
            if key not in legacy or key not in snapshot:
                differences.append(child_path)
            else:
                differences.extend(
                    _find_differences(legacy[key], snapshot[key], child_path)
                )
        return differences

    if isinstance(legacy, list) and isinstance(snapshot, list):
        differences = []
        if len(legacy) != len(snapshot):
            differences.append(f"{path}.length")
        for left, right in zip(legacy, snapshot):
            differences.extend(_find_differences(left, right, f"{path}[]"))
        return differences

    return [] if legacy == snapshot else [path]
