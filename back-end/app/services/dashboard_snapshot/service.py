"""Dashboard snapshot service for publishing to Redis.

Implements Phase 1 of the migration: publish shared finite dashboard/outage
snapshot using the versioned schema, atomic Redis write with lease fencing and
CAS on (epoch, version), and invalidation notification.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from injector import inject
from redis.asyncio import Redis

from shared.features import feature_flags, FeatureFlag
from shared.metrics import (
    DASHBOARD_SNAPSHOT_BUILD_DURATION,
    DASHBOARD_SNAPSHOT_PUBLISH_DURATION,
    DASHBOARD_SNAPSHOT_EPOCH,
    DASHBOARD_SNAPSHOT_VERSION,
    DASHBOARD_SNAPSHOT_AGE_SECONDS,
    DASHBOARD_SNAPSHOT_WRITE_ERRORS,
    DASHBOARD_REFRESH_REQUESTS,
    DASHBOARD_REFRESH_COALESCED,
)
from shared.services.events.service import EventsService
from shared.services.dashboard import ReadOnlyDashboardService
from shared.services.outages_schedule import OutagesScheduleService
from shared.services.settings.service import SettingsService
from app.repositories import (
    IDashboardRepository,
    IStationsRepository,
    IStationsDataRepository,
    IExtDataRepository,
    IUsersRepository,
    IOutagesScheduleRepository,
)
from app.settings import Settings
from app.services.dashboard_snapshot.models import (
    DashboardSnapshot,
    BuildingSnapshot,
    ConfigSnapshot,
    UnitScheduleSnapshot,
    DayScheduleSnapshot,
    SlotSnapshot,
    LocalizableValue,
)

logger = logging.getLogger(__name__)

# Redis keys per redis-conventions.md
SNAPSHOT_KEY = "cache:dashboard:v1:global"
INVALIDATION_CHANNEL = "cache:dashboard:v1:invalidations"
LEASE_KEY = "lock:processing:dashboard:v1"
EPOCH_KEY = "meta:dashboard:epoch"
VERSION_NEXT_KEY = "meta:dashboard:version:next"
VERSION_COMMITTED_KEY = "meta:dashboard:version"

LEASE_TTL_SECONDS = 30
LEASE_RENEW_INTERVAL_SECONDS = 10
SNAPSHOT_TTL_SECONDS = 86400

# Lua script for atomic write with lease fencing and CAS on (epoch, version)
LUA_WRITE_SCRIPT = """
local snapshot_json = ARGV[1]
local notification_json = ARGV[2]
local ttl = tonumber(ARGV[3])
local lease_token = ARGV[4]
local expected_epoch = tonumber(ARGV[5])
local expected_version = tonumber(ARGV[6])

-- 1. Verify lease holder (fencing)
local current_lease = redis.call('GET', KEYS[3])
if current_lease ~= lease_token then
  return {0, 'lease-lost', 'not-lease-holder'}
end

-- 2. Compare-and-set on (epoch, committed_version)
local current_epoch = tonumber(redis.call('GET', KEYS[4]) or '0')
local current_version = tonumber(redis.call('GET', KEYS[5]) or '0')

if expected_epoch < current_epoch then
  return {0, 'epoch-stale', 'expected-epoch ' .. expected_epoch .. ' < current ' .. current_epoch}
end
if expected_epoch == current_epoch and expected_version <= current_version then
  return {0, 'version-stale', 'expected-version ' .. expected_version .. ' <= current ' .. current_version}
end

-- 3. Write snapshot atomically
redis.call('SET', KEYS[1], snapshot_json, 'EX', ttl)

-- 4. Update committed version (epoch is set once at producer start)
redis.call('SET', KEYS[5], expected_version)

-- 5. Publish invalidation
redis.call('PUBLISH', KEYS[2], notification_json)

return {1, 'ok', 'epoch=' .. expected_epoch .. ',version=' .. expected_version}
"""


class DashboardSnapshotService:
    """Builds and publishes dashboard snapshots to Redis."""

    @inject
    def __init__(
        self,
        events: EventsService,
        dashboard: ReadOnlyDashboardService,
        dashboard_repo: IDashboardRepository,
        stations: IStationsRepository,
        stations_data: IStationsDataRepository,
        ext_data: IExtDataRepository,
        users: IUsersRepository,
        outages_schedule: OutagesScheduleService,
        outages_repo: IOutagesScheduleRepository,
        settings: Settings,
    ):
        self._events = events
        self._dashboard = dashboard
        self._dashboard_repo = dashboard_repo
        self._stations = stations
        self._stations_data = stations_data
        self._ext_data = ext_data
        self._users = users
        self._outages_schedule = outages_schedule
        self._outages_repo = outages_repo
        self._settings = settings

        self._redis: Optional[Redis] = Redis.from_url(
            str(settings.REDIS_URI), decode_responses=True
        )
        self._lease_token: Optional[str] = None
        self._epoch: Optional[int] = None
        self._version: Optional[int] = None
        self._lease_renew_task: Optional[asyncio.Task] = None
        self._refresh_lock = asyncio.Lock()
        self._refresh_event = asyncio.Event()
        self._refresh_scheduled = False
        self._last_snapshot: Optional[DashboardSnapshot] = None
        self._start_time_ms: Optional[int] = None

    @property
    def is_publish_enabled(self) -> bool:
        return feature_flags.is_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH)

    async def start(self) -> None:
        """Initialize epoch, acquire lease, and publish initial snapshot."""
        self._start_time_ms = int(time.time() * 1000)
        self._epoch = self._start_time_ms

        if self.is_publish_enabled:
            await self._acquire_lease()
            await self._init_version_keys()
            await self.refresh_and_publish()
            self._lease_renew_task = asyncio.create_task(self._lease_renew_loop())

    async def stop(self) -> None:
        """Release lease and stop background tasks."""
        if self._lease_renew_task:
            self._lease_renew_task.cancel()
            try:
                await self._lease_renew_task
            except asyncio.CancelledError:
                pass
            self._lease_renew_task = None

        if self.is_publish_enabled and self._lease_token:
            await self._release_lease()

    async def _acquire_lease(self) -> bool:
        """Acquire the processing lease."""
        self._lease_token = f"back-end-{int(time.time() * 1000)}"
        result = await self._redis.set(
            LEASE_KEY, self._lease_token, nx=True, ex=LEASE_TTL_SECONDS
        )
        acquired = result is True
        if acquired:
            logger.info("Dashboard snapshot lease acquired: %s", self._lease_token)
        else:
            logger.warning("Failed to acquire dashboard snapshot lease")
            self._lease_token = None
        return acquired

    async def _release_lease(self) -> None:
        """Release the processing lease if we hold it."""
        if not self._lease_token:
            return
        release_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
          return redis.call('DEL', KEYS[1])
        else
          return 0
        end
        """
        try:
            await self._redis.eval(
                release_script,
                1,
                LEASE_KEY,
                self._lease_token,
            )
            logger.info("Dashboard snapshot lease released: %s", self._lease_token)
        except Exception as e:
            logger.warning("Error releasing lease: %s", e)
        self._lease_token = None

    async def _lease_renew_loop(self) -> None:
        """Periodically renew the lease."""
        while True:
            try:
                await asyncio.sleep(LEASE_RENEW_INTERVAL_SECONDS)
                await self._renew_lease()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Lease renewal error: %s", e)

    async def _renew_lease(self) -> None:
        """Renew the lease if we hold it."""
        if not self._lease_token:
            return
        renew_script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
          return redis.call('EXPIRE', KEYS[1], 30)
        else
          return 0
        end
        """
        try:
            result = await self._redis.eval(
                renew_script, 1, LEASE_KEY, self._lease_token
            )
            if result == 0:
                logger.warning("Lease lost, cannot renew: %s", self._lease_token)
                self._lease_token = None
        except Exception as e:
            logger.warning("Lease renewal error: %s", e)

    async def _init_version_keys(self) -> None:
        """Initialize epoch and version allocator keys if not present."""
        # Set epoch if not already set (survives Redis flush)
        existing_epoch = await self._redis.get(EPOCH_KEY)
        if existing_epoch is None:
            await self._redis.set(EPOCH_KEY, self._epoch)

        # Initialize version allocator to 1 if not present
        existing_next = await self._redis.get(VERSION_NEXT_KEY)
        if existing_next is None:
            await self._redis.set(VERSION_NEXT_KEY, 1)

        # Initialize committed version to 0 if not present
        existing_committed = await self._redis.get(VERSION_COMMITTED_KEY)
        if existing_committed is None:
            await self._redis.set(VERSION_COMMITTED_KEY, 0)

    async def build_snapshot(self) -> DashboardSnapshot:
        """Build a DashboardSnapshot from current data sources."""
        with DASHBOARD_SNAPSHOT_BUILD_DURATION.time():
            # Get config
            config = await self._dashboard.get_config()

            # Get buildings with summary
            buildings_with_summary = await self._dashboard.get_buildings_with_summary()

            # Get all outage schedules
            all_schedules = await self._outages_repo.get_all_schedules()

            # Build building snapshots
            building_snapshots = []
            for building in buildings_with_summary:
                building_snapshots.append(
                    BuildingSnapshot(
                        id=str(building.id),
                        name=building.name.root,
                        color=building.color,
                        order=building.order,
                        has_bound_station=building.has_bound_station,
                        is_grid_available=building.is_grid_available,
                        grid_availability_pct=building.grid_availability_pct,
                        has_mixed_reporter_states=building.has_mixed_reporter_states,
                        is_charging=building.is_charging,
                        is_discharging=building.is_discharging,
                        is_offline=building.is_offline,
                        battery_percent=building.battery_percent,
                        consumption_power=building.consumption_power,
                        battery_discharge_time=building.battery_discharge_time,
                        battery_charge_time=building.battery_charge_time,
                        charge_source=building.charge_source.value
                        if hasattr(building.charge_source, "value")
                        else str(building.charge_source),
                        charge_power=building.charge_power,
                    )
                )

            # Build config snapshot
            outages_schedule = config.outages_schedule
            config_snapshot = ConfigSnapshot(
                title=(
                    config.title.root
                    if hasattr(config.title, "root")
                    else config.title
                ),
                outages_schedule=(
                    {
                        "enable": outages_schedule.enable,
                        "region_id": outages_schedule.region_id,
                        "dso_id": outages_schedule.dso_id,
                        "queue": outages_schedule.queue,
                    }
                    if outages_schedule
                    else None
                ),
            )

            # Build outages schedules snapshot
            outages_schedules = {}
            for queue, unit_schedule in all_schedules.root.items():
                days = []
                for day in unit_schedule.days:
                    slots = [
                        SlotSnapshot(
                            start=slot.start,
                            end=slot.end,
                            type=slot.type.value
                            if hasattr(slot.type, "value")
                            else str(slot.type),
                        )
                        for slot in day.slots
                    ]
                    days.append(
                        DayScheduleSnapshot(
                            slots=slots,
                            date=day.date,
                            status=day.status.value
                            if hasattr(day.status, "value")
                            else str(day.status),
                        )
                    )
                outages_schedules[queue] = UnitScheduleSnapshot(
                    days=days,
                    updatedOn=unit_schedule.updatedOn,
                )

            snapshot = DashboardSnapshot(
                epoch=self._epoch or int(time.time() * 1000),
                version=self._version or 1,
                generated_at=datetime.now(timezone.utc),
                buildings=building_snapshots,
                config=config_snapshot,
                outages_schedules=outages_schedules,
            )

            DASHBOARD_SNAPSHOT_EPOCH.set(snapshot.epoch)
            DASHBOARD_SNAPSHOT_VERSION.set(snapshot.version)
            age = (datetime.now(timezone.utc) - snapshot.generated_at).total_seconds()
            DASHBOARD_SNAPSHOT_AGE_SECONDS.set(age)

            return snapshot

    async def publish_snapshot(self, snapshot: DashboardSnapshot) -> bool:
        """Publish snapshot to Redis atomically with lease fencing and CAS."""
        if not self.is_publish_enabled:
            return True

        if not self._lease_token:
            logger.warning("Cannot publish snapshot: no lease held")
            DASHBOARD_SNAPSHOT_WRITE_ERRORS.labels(error_type="no-lease").inc()
            return False

        try:
            with DASHBOARD_SNAPSHOT_PUBLISH_DURATION.time():
                snapshot_json = snapshot.model_dump_json()
                notification = {
                    "key": SNAPSHOT_KEY,
                    "epoch": snapshot.epoch,
                    "version": snapshot.version,
                    "generatedAt": snapshot.generated_at.isoformat(),
                }
                notification_json = json.dumps(notification)

                result = await self._redis.eval(
                    LUA_WRITE_SCRIPT,
                    5,
                    SNAPSHOT_KEY,
                    INVALIDATION_CHANNEL,
                    LEASE_KEY,
                    EPOCH_KEY,
                    VERSION_COMMITTED_KEY,
                    snapshot_json,
                    notification_json,
                    SNAPSHOT_TTL_SECONDS,
                    self._lease_token,
                    snapshot.epoch,
                    snapshot.version,
                )

            success = result[0] == 1
            if success:
                self._version = snapshot.version
                DASHBOARD_SNAPSHOT_VERSION.set(snapshot.version)
                age = (
                    datetime.now(timezone.utc) - snapshot.generated_at
                ).total_seconds()
                DASHBOARD_SNAPSHOT_AGE_SECONDS.set(age)
                logger.info(
                    "Snapshot published: epoch=%d, version=%d",
                    snapshot.epoch,
                    snapshot.version,
                )
            else:
                reason = result[1] if len(result) > 1 else "unknown"
                logger.warning(
                    "Snapshot publish rejected: %s (epoch=%d, version=%d)",
                    reason,
                    snapshot.epoch,
                    snapshot.version,
                )
                DASHBOARD_SNAPSHOT_WRITE_ERRORS.labels(
                    error_type=str(reason)
                ).inc()

            return success
        except Exception as e:
            logger.error("Error publishing snapshot: %s", e)
            DASHBOARD_SNAPSHOT_WRITE_ERRORS.labels(error_type="exception").inc()
            return False

    async def refresh_and_publish(self) -> DashboardSnapshot:
        """Build and publish a fresh snapshot."""
        snapshot = await self.build_snapshot()
        await self.publish_snapshot(snapshot)
        self._last_snapshot = snapshot
        return snapshot

    async def handle_refresh_request(
        self, reason: str, requested_by: str
    ) -> dict:
        """Handle an HTTP refresh request with server-side coalescing."""
        DASHBOARD_REFRESH_REQUESTS.labels(reason=reason).inc()

        # If a refresh is already scheduled, coalesce this request
        async with self._refresh_lock:
            if self._refresh_scheduled:
                DASHBOARD_REFRESH_COALESCED.inc()
                # Wait for the in-flight refresh to complete
                await self._refresh_event.wait()
                if self._last_snapshot:
                    return {
                        "accepted": True,
                        "epoch": self._last_snapshot.epoch,
                        "version": self._last_snapshot.version,
                        "coalesced": True,
                    }
                return {"accepted": True, "coalesced": True}

            self._refresh_scheduled = True

        try:
            # Debounce: wait briefly to coalesce concurrent requests
            await asyncio.sleep(0.5)

            snapshot = await self.refresh_and_publish()
            return {
                "accepted": True,
                "epoch": snapshot.epoch,
                "version": snapshot.version,
                "coalesced": False,
            }
        finally:
            async with self._refresh_lock:
                self._refresh_scheduled = False
                self._refresh_event.set()
                self._refresh_event.clear()
