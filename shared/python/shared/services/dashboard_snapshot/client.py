"""Reusable local Redis consumer for dashboard snapshots."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError
from pydantic import ValidationError

from shared.metrics import (
    REDIS_SNAPSHOT_AGE_SECONDS,
    REDIS_SNAPSHOT_CACHE_MISS_TOTAL,
    REDIS_SNAPSHOT_RECONCILIATION_TOTAL,
    REDIS_SNAPSHOT_VERSION_LAG,
)
from shared.models.dashboard_snapshot import (
    BuildingSnapshot,
    ConfigSnapshot,
    DashboardSnapshot,
    UnitScheduleSnapshot,
)

logger = logging.getLogger(__name__)

SNAPSHOT_KEY = "cache:dashboard:v1:global"
INVALIDATION_CHANNEL = "cache:dashboard:v1:invalidations"


class DashboardSnapshotClient:
    def __init__(
        self,
        redis: Redis,
        session: aiohttp.ClientSession,
        refresh_url: str,
        stale_threshold_seconds: int = 300,
        reconciliation_interval_seconds: int = 60,
        refresh_wait_seconds: float = 5,
        requested_by: str = "shared-consumer",
    ):
        self._redis = redis
        self._session = session
        self._refresh_url = refresh_url
        self._requested_by = requested_by
        self._stale_threshold_seconds = stale_threshold_seconds
        self._reconciliation_interval_seconds = reconciliation_interval_seconds
        self._refresh_wait_seconds = refresh_wait_seconds
        self._snapshot: DashboardSnapshot | None = None
        self._redis_epoch = 0
        self._redis_version = 0
        self._last_notification_at: datetime | None = None
        self._subscribed = False
        self._stopped = False
        self._subscriber_task: asyncio.Task | None = None
        self._reconciliation_task: asyncio.Task | None = None
        self._age_metrics_task: asyncio.Task | None = None
        self._pubsub: Any = None
        self._connected = asyncio.Event()
        self._initial_reconcile_complete = asyncio.Event()
        self._notification_received = asyncio.Event()
        self._refresh_lock = asyncio.Lock()
        self._version_lag_since: float | None = None

    async def start(self) -> None:
        """Subscribe before the initial read, then keep the local copy reconciled."""
        if self._subscriber_task:
            return

        self._stopped = False
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        self._reconciliation_task = asyncio.create_task(self._reconciliation_loop())
        self._age_metrics_task = asyncio.create_task(self._age_metrics_loop())
        try:
            await asyncio.wait_for(self._connected.wait(), timeout=5)
            await asyncio.wait_for(self._initial_reconcile_complete.wait(), timeout=5)
        except asyncio.TimeoutError:
            logger.warning("Dashboard snapshot subscription is not yet available")

        if self._snapshot is None:
            await self._refresh_on_cache_miss()

    async def stop(self) -> None:
        self._stopped = True
        self._subscribed = False
        self._connected.clear()

        tasks = [
            task for task in (
                self._subscriber_task,
                self._reconciliation_task,
                self._age_metrics_task,
            )
            if task is not None
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._subscriber_task = None
        self._reconciliation_task = None
        self._age_metrics_task = None
        self._pubsub = None

    def get_snapshot(self) -> DashboardSnapshot | None:
        return self._snapshot

    def get_buildings(self) -> list[BuildingSnapshot]:
        return self._snapshot.buildings if self._snapshot else []

    def get_building(self, building_id: str) -> BuildingSnapshot | None:
        return next(
            (building for building in self.get_buildings() if building.id == building_id),
            None,
        )

    def get_config(self) -> ConfigSnapshot | None:
        return self._snapshot.config if self._snapshot else None

    def get_outages_schedule(self, queue: str) -> UnitScheduleSnapshot | None:
        if self._snapshot is None:
            return None
        return self._snapshot.outages_schedules.get(queue)

    @property
    def epoch(self) -> int:
        return self._snapshot.epoch if self._snapshot else 0

    @property
    def version(self) -> int:
        return self._snapshot.version if self._snapshot else 0

    @property
    def age_seconds(self) -> float:
        if self._snapshot is None:
            return float("inf")
        age = (datetime.now(timezone.utc) - self._snapshot.generated_at).total_seconds()
        return max(0.0, age)

    @property
    def is_stale(self) -> bool:
        return self._snapshot is None or self.age_seconds > self._stale_threshold_seconds

    @property
    def is_subscribed(self) -> bool:
        return self._subscribed

    @property
    def redis_epoch(self) -> int:
        return self._redis_epoch

    @property
    def redis_version(self) -> int:
        return self._redis_version

    @property
    def version_lag(self) -> int:
        if self._redis_epoch != self.epoch:
            return 0
        return max(0, self._redis_version - self.version)

    @property
    def last_notification_at(self) -> datetime | None:
        return self._last_notification_at

    def health(self) -> dict[str, Any]:
        lag = self.version_lag
        now = asyncio.get_running_loop().time()
        if lag > 1:
            if self._version_lag_since is None:
                self._version_lag_since = now
        else:
            self._version_lag_since = None

        unhealthy = (
            not self._subscribed
            or self.is_stale and self.age_seconds > 600
            or self._snapshot is None
            or self._redis_epoch not in (0, self.epoch)
            or (
                lag > 1
                and self._version_lag_since is not None
                and now - self._version_lag_since > 60
            )
        )
        return {
            "status": "unhealthy" if unhealthy else "healthy",
            "localEpoch": self.epoch,
            "localVersion": self.version,
            "redisEpoch": self._redis_epoch,
            "redisVersion": self._redis_version,
            "versionLag": lag,
            "snapshotAgeSeconds": (
                self.age_seconds if self._snapshot is not None else None
            ),
            "isStale": self.is_stale,
            "subscribed": self._subscribed,
            "lastNotificationAt": (
                self._last_notification_at.isoformat()
                if self._last_notification_at
                else None
            ),
        }

    async def reconcile(self) -> None:
        """Read Redis and adopt only snapshots newer than the local version."""
        try:
            raw_snapshot = await self._redis.get(SNAPSHOT_KEY)
            if raw_snapshot is None:
                REDIS_SNAPSHOT_CACHE_MISS_TOTAL.inc()
                REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="stale").inc()
                REDIS_SNAPSHOT_AGE_SECONDS.set(self.age_seconds)
                return

            snapshot = DashboardSnapshot.model_validate_json(raw_snapshot)
            self._redis_epoch = snapshot.epoch
            self._redis_version = snapshot.version
            lag = self.version_lag
            REDIS_SNAPSHOT_VERSION_LAG.set(lag)
            if lag > 1 and self._version_lag_since is None:
                self._version_lag_since = asyncio.get_running_loop().time()
            elif lag <= 1:
                self._version_lag_since = None

            if (snapshot.epoch, snapshot.version) > (self.epoch, self.version):
                self._snapshot = snapshot
                self._version_lag_since = None
            elif (snapshot.epoch, snapshot.version) < (self.epoch, self.version):
                REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="stale").inc()
                return

            REDIS_SNAPSHOT_AGE_SECONDS.set(self.age_seconds)
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="ok").inc()
        except (ConnectionError, TimeoutError, ValidationError, ValueError):
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="error").inc()
            logger.exception("Could not reconcile dashboard snapshot from Redis")
        except Exception:
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="error").inc()
            logger.exception("Unexpected dashboard snapshot reconciliation failure")

    async def _subscriber_loop(self) -> None:
        backoff = 1.0
        while not self._stopped:
            pubsub = self._redis.pubsub()
            self._pubsub = pubsub
            try:
                await pubsub.subscribe(INVALIDATION_CHANNEL)
                self._subscribed = True
                self._connected.set()
                await self.reconcile()
                self._initial_reconcile_complete.set()
                backoff = 1.0

                async for message in pubsub.listen():
                    if self._stopped:
                        break
                    if not message or message.get("type") != "message":
                        continue
                    await self._handle_notification(message.get("data"))

                if not self._stopped:
                    raise ConnectionError("Dashboard invalidation listener ended")
            except asyncio.CancelledError:
                raise
            except (ConnectionError, TimeoutError):
                self._subscribed = False
                self._connected.clear()
                logger.warning(
                    "Lost dashboard snapshot subscription; reconnecting in %.1fs",
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10)
            except Exception:
                self._subscribed = False
                self._connected.clear()
                logger.exception("Dashboard snapshot subscriber failed")
                await asyncio.sleep(1)
                backoff = 1.0
            finally:
                if self._pubsub is pubsub:
                    self._pubsub = None
                try:
                    await pubsub.aclose()
                except Exception:
                    logger.debug("Error closing dashboard snapshot pubsub", exc_info=True)

    async def _handle_notification(self, payload: str | bytes | None) -> None:
        try:
            notification = json.loads(payload)
            if notification.get("key", SNAPSHOT_KEY) != SNAPSHOT_KEY:
                return
            notification_version = (
                int(notification["epoch"]),
                int(notification["version"]),
            )
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            logger.warning("Ignoring invalid dashboard snapshot invalidation")
            return

        self._last_notification_at = datetime.now(timezone.utc)
        if notification_version > (self.epoch, self.version):
            await self.reconcile()
        self._notification_received.set()

    async def _reconciliation_loop(self) -> None:
        while not self._stopped:
            try:
                await asyncio.sleep(self._reconciliation_interval_seconds)
                await self.reconcile()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Dashboard snapshot reconciliation loop failed")

    async def _age_metrics_loop(self) -> None:
        while not self._stopped:
            try:
                await asyncio.sleep(15)
                REDIS_SNAPSHOT_AGE_SECONDS.set(self.age_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Dashboard snapshot age metric update failed")

    async def _refresh_on_cache_miss(self) -> None:
        async with self._refresh_lock:
            if self._snapshot is not None:
                return
            self._notification_received.clear()
            try:
                async with self._session.post(
                    self._refresh_url,
                    json={"reason": "cache-miss", "requestedBy": self._requested_by},
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    response.raise_for_status()
            except (aiohttp.ClientError, asyncio.TimeoutError):
                logger.exception("Dashboard snapshot refresh request failed")
                return

            try:
                await asyncio.wait_for(
                    self._notification_received.wait(),
                    timeout=self._refresh_wait_seconds,
                )
            except asyncio.TimeoutError:
                logger.warning("No dashboard snapshot notification after refresh request")
            await self.reconcile()
