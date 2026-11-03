"""Redis-backed dashboard snapshot client for app-back-end.

Implements Phase 2 of the migration: subscribe-before-read, reconnect recovery,
reconciliation, and cache-miss refresh via the producer HTTP endpoint.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as redis

from app.clients.snapshot_models import (
    DashboardSnapshot,
    BuildingSnapshot,
    ConfigSnapshot,
    UnitSchedule,
)
from shared.features import feature_flags, FeatureFlag
from shared.metrics import (
    DASHBOARD_SNAPSHOT_EPOCH,
    DASHBOARD_SNAPSHOT_VERSION,
    DASHBOARD_SNAPSHOT_AGE_SECONDS,
    REDIS_SNAPSHOT_VERSION_LAG,
    REDIS_SNAPSHOT_RECONCILIATION_TOTAL,
    REDIS_SNAPSHOT_CACHE_MISS_TOTAL,
)

logger = logging.getLogger(__name__)

# Redis keys per redis-conventions.md
SNAPSHOT_KEY = "cache:dashboard:v1:global"
INVALIDATION_CHANNEL = "cache:dashboard:v1:invalidations"

# Default thresholds
DEFAULT_STALE_THRESHOLD_SECONDS = 300
RECONCILIATION_INTERVAL_SECONDS = 60
CACHE_MISS_WAIT_SECONDS = 5


class DashboardSnapshotClient:
    """Client that maintains a local copy of the dashboard snapshot from Redis.

    Subscribes to invalidation notifications, reconciles periodically, and falls
    back to an HTTP refresh request on cache miss.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        *,
        stale_threshold_seconds: int = DEFAULT_STALE_THRESHOLD_SECONDS,
        producer_refresh_url: Optional[str] = None,
        aiohttp_session=None,
    ) -> None:
        self._redis = redis_client
        self._stale_threshold_seconds = stale_threshold_seconds
        self._producer_refresh_url = producer_refresh_url
        self._aiohttp_session = aiohttp_session

        self._snapshot: Optional[DashboardSnapshot] = None
        self._local_epoch: Optional[int] = None
        self._local_version: Optional[int] = None
        self._last_notification_at: Optional[datetime] = None
        self._subscribed = False

        self._pubsub: Optional[redis.client.PubSub] = None
        _subscriber_task: Optional[asyncio.Task] = None
        self._reconciliation_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

    @property
    def epoch(self) -> Optional[int]:
        return self._local_epoch

    @property
    def version(self) -> Optional[int]:
        return self._local_version

    @property
    def is_stale(self) -> bool:
        if self._snapshot is None or self._snapshot.generated_at is None:
            return True
        age = (datetime.now(timezone.utc) - self._snapshot.generated_at).total_seconds()
        return age > self._stale_threshold_seconds

    @property
    def age_seconds(self) -> float:
        if self._snapshot is None or self._snapshot.generated_at is None:
            return float("inf")
        return (datetime.now(timezone.utc) - self._snapshot.generated_at).total_seconds()

    @property
    def subscribed(self) -> bool:
        return self._subscribed

    def get_snapshot(self) -> Optional[DashboardSnapshot]:
        """Return current local snapshot (never blocks)."""
        return self._snapshot

    def get_buildings(self) -> list[BuildingSnapshot]:
        """Return buildings from snapshot."""
        if self._snapshot is None:
            return []
        return self._snapshot.buildings

    def get_building(self, building_id: str) -> Optional[BuildingSnapshot]:
        """Return a single building by id."""
        if self._snapshot is None:
            return None
        for building in self._snapshot.buildings:
            if building.id == building_id:
                return building
        return None

    def get_config(self) -> Optional[ConfigSnapshot]:
        """Return dashboard config from snapshot."""
        if self._snapshot is None:
            return None
        return self._snapshot.config

    def get_outages_schedule(self, queue: str) -> Optional[UnitSchedule]:
        """Return outage schedule for a queue."""
        if self._snapshot is None:
            return None
        return self._snapshot.outages_schedules.get(queue)

    async def start(self) -> None:
        """Subscribe, load initial snapshot, start reconciliation loop."""
        self._stop_event.clear()

        # Subscribe to invalidation channel
        self._pubsub = self._redis.pubsub()
        await self._pubsub.subscribe(INVALIDATION_CHANNEL)
        self._subscribed = True
        logger.info("Subscribed to %s", INVALIDATION_CHANNEL)

        # Load initial snapshot
        await self._load_snapshot_from_redis()

        # Start background tasks
        self._subscriber_task = asyncio.create_task(self._subscriber_loop())
        self._reconciliation_task = asyncio.create_task(self._reconciliation_loop())

    async def stop(self) -> None:
        """Stop background tasks and unsubscribe."""
        self._stop_event.set()

        if self._subscriber_task:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            self._subscriber_task = None

        if self._reconciliation_task:
            self._reconciliation_task.cancel()
            try:
                await self._reconciliation_task
            except asyncio.CancelledError:
                pass
            self._reconciliation_task = None

        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(INVALIDATION_CHANNEL)
                await self._pubsub.close()
            except Exception as e:
                logger.warning("Error closing pubsub: %s", e)
            self._pubsub = None
            self._subscribed = False

    async def _subscriber_loop(self) -> None:
        """Listen for invalidation notifications and update local snapshot."""
        assert self._pubsub is not None
        while not self._stop_event.is_set():
            try:
                message = await asyncio.wait_for(
                    self._pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.warning("Pubsub get_message error: %s", e)
                await self._handle_reconnect()
                continue

            if message is None:
                continue

            try:
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                notification = json.loads(data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Invalid notification message: %s", e)
                continue

            epoch = notification.get("epoch")
            version = notification.get("version")
            if epoch is None or version is None:
                continue

            if self._is_newer(epoch, version):
                await self._load_snapshot_from_redis()
                self._last_notification_at = datetime.now(timezone.utc)

    async def _reconciliation_loop(self) -> None:
        """Periodically reconcile local snapshot with Redis."""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(RECONCILIATION_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            if self._stop_event.is_set():
                break
            try:
                await self._reconcile()
            except Exception as e:
                logger.warning("Reconciliation error: %s", e)

    async def _reconcile(self) -> None:
        """GET snapshot key and compare (epoch, version) with local."""
        snapshot_json = await self._redis.get(SNAPSHOT_KEY)
        if snapshot_json is None:
            logger.warning("Reconciliation: snapshot key missing in Redis")
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="error").inc()
            await self._handle_cache_miss()
            return

        try:
            snapshot = DashboardSnapshot.model_validate_json(snapshot_json)
        except Exception as e:
            logger.warning("Reconciliation: failed to parse snapshot: %s", e)
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="error").inc()
            return

        if self._local_epoch is not None and self._local_version is not None:
            lag = snapshot.version - self._local_version
            REDIS_SNAPSHOT_VERSION_LAG.set(max(lag, 0))

        if self._is_newer(snapshot.epoch, snapshot.version):
            self._update_local(snapshot)
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="ok").inc()
            logger.info(
                "Reconciliation updated snapshot: epoch=%d, version=%d",
                snapshot.epoch,
                snapshot.version,
            )
        else:
            REDIS_SNAPSHOT_RECONCILIATION_TOTAL.labels(result="ok").inc()

    async def _load_snapshot_from_redis(self) -> None:
        """GET snapshot key and update local if newer."""
        snapshot_json = await self._redis.get(SNAPSHOT_KEY)
        if snapshot_json is None:
            logger.warning("Snapshot key missing in Redis, handling cache miss")
            await self._handle_cache_miss()
            return

        try:
            snapshot = DashboardSnapshot.model_validate_json(snapshot_json)
        except Exception as e:
            logger.warning("Failed to parse snapshot from Redis: %s", e)
            return

        if self._is_newer(snapshot.epoch, snapshot.version):
            self._update_local(snapshot)
            logger.info(
                "Loaded snapshot from Redis: epoch=%d, version=%d",
                snapshot.epoch,
                snapshot.version,
            )

    async def _handle_cache_miss(self) -> None:
        """On cache miss: call HTTP refresh endpoint, wait for notification, then GET."""
        REDIS_SNAPSHOT_CACHE_MISS_TOTAL.inc()
        if self._producer_refresh_url is None or self._aiohttp_session is None:
            logger.warning("Cache miss but no producer refresh URL or session configured")
            return

        try:
            async with self._aiohttp_session.post(
                self._producer_refresh_url,
                json={"reason": "cache-miss", "requestedBy": "app-back-end"},
            ) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    logger.info(
                        "Cache miss refresh accepted: epoch=%s, version=%s",
                        body.get("epoch"),
                        body.get("version"),
                    )
                else:
                    logger.warning(
                        "Cache miss refresh returned status %s", resp.status
                    )
        except Exception as e:
            logger.warning("Cache miss refresh request failed: %s", e)

        # Wait for notification (max 5s), then GET
        try:
            await asyncio.wait_for(self._wait_for_newer_notification(), timeout=CACHE_MISS_WAIT_SECONDS)
        except asyncio.TimeoutError:
            logger.warning("Cache miss: timed out waiting for notification")

        await self._load_snapshot_from_redis()

    async def _wait_for_newer_notification(self) -> None:
        """Wait until a newer notification arrives or stop is requested."""
        # This is a simple polling approach: check if snapshot became newer
        while not self._stop_event.is_set():
            snapshot_json = await self._redis.get(SNAPSHOT_KEY)
            if snapshot_json is not None:
                try:
                    snapshot = DashboardSnapshot.model_validate_json(snapshot_json)
                    if self._is_newer(snapshot.epoch, snapshot.version):
                        return
                except Exception:
                    pass
            await asyncio.sleep(0.2)

    async def _handle_reconnect(self) -> None:
        """Re-subscribe to invalidation channel and reload snapshot."""
        logger.warning("Handling Redis reconnect")
        try:
            if self._pubsub:
                await self._pubsub.close()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.subscribe(INVALIDATION_CHANNEL)
            self._subscribed = True
            await self._load_snapshot_from_redis()
            logger.info("Reconnected and re-subscribed to %s", INVALIDATION_CHANNEL)
        except Exception as e:
            logger.warning("Reconnect failed: %s", e)

    def _is_newer(self, epoch: int, version: int) -> bool:
        """Check if (epoch, version) is newer than local."""
        if self._local_epoch is None or self._local_version is None:
            return True
        if epoch > self._local_epoch:
            return True
        if epoch == self._local_epoch and version > self._local_version:
            return True
        return False

    def _update_local(self, snapshot: DashboardSnapshot) -> None:
        """Update local snapshot and metrics."""
        self._snapshot = snapshot
        self._local_epoch = snapshot.epoch
        self._local_version = snapshot.version

        DASHBOARD_SNAPSHOT_EPOCH.set(snapshot.epoch)
        DASHBOARD_SNAPSHOT_VERSION.set(snapshot.version)
        DASHBOARD_SNAPSHOT_AGE_SECONDS.set(self.age_seconds)
