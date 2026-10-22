import hashlib
import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone, tzinfo

from injector import inject

from shared.services.outages_schedule import OutagesScheduleService, ScheduleUpdate
from shared.services.outages_schedule.models import DaySchedule, DayStatus, UnitSchedule
from app.repositories import IDashboardRepository
from ..dispatcher import PushEventDispatcher
from ..events import LEAD_MINUTES, PushEvent, schedule_slot
from ..templates import PushTemplatesService
from ..topics import EMERGENCY, OUTAGE_UPCOMING, SCHEDULE_CHANGES


logger = logging.getLogger(__name__)

MINUTES_PER_DAY = 24 * 60


def merge_slots(day: DaySchedule) -> list[tuple[int, int]]:
    """Outage periods of the day; adjacent slots (08:00–10:00, 10:00–12:00) are one outage."""
    periods: list[tuple[int, int]] = []
    for slot in sorted(day.slots, key=lambda s: s.start):
        if periods and slot.start <= periods[-1][1]:
            periods[-1] = (periods[-1][0], max(periods[-1][1], slot.end))
        else:
            periods.append((slot.start, slot.end))
    return periods


def local_date(day: DaySchedule, tz: tzinfo) -> date:
    value = day.date if day.date.tzinfo else day.date.replace(tzinfo=tz)
    return value.astimezone(tz).date()


def _day_name(day_date: date, today: date) -> str:
    if day_date == today:
        return "today"
    if day_date == today + timedelta(days=1):
        return "tomorrow"
    return day_date.isoformat()


def _slots_hash(periods: list[tuple[int, int]]) -> str:
    text = ";".join(f"{start}-{end}" for start, end in periods)
    return hashlib.sha1(text.encode()).hexdigest()[:12]


def schedule_events(update: ScheduleUpdate, queue: str, tz: tzinfo, today: date) -> list[PushEvent]:
    """Schedule change and emergency events of the queue between the stored and the new schedule."""
    if update.previous is None:
        # First fetch: the stored schedule becomes the baseline
        return []
    previous: UnitSchedule | None = update.previous.root.get(queue)
    current: UnitSchedule | None = update.current.root.get(queue)
    if previous is None or current is None:
        return []

    previous_days = { local_date(d, tz): d for d in previous.days }
    events: list[PushEvent] = []

    for day in current.days:
        day_date = local_date(day, tz)
        before = previous_days.get(day_date)
        # A day that just appeared (e.g. tomorrow after midnight) had no schedule yet
        before_status = before.status if before else DayStatus.WaitingForSchedule
        before_periods = merge_slots(before) if before else []
        periods = merge_slots(day)

        common = {
            "queue": queue,
            "day": _day_name(day_date, today),
            "date": day_date,
            "status": day.status.value,
        }

        if (before_status == DayStatus.EmergencyShutdowns) != (day.status == DayStatus.EmergencyShutdowns):
            active = day.status == DayStatus.EmergencyShutdowns
            events.append(PushEvent(
                topic       = EMERGENCY,
                dedup_key   = f"emergency:{queue}:{day_date.isoformat()}:{day.status.value}",
                context     = { **common, "previous_status": before_status.value, "active": active },
                summary     = { "queue": queue, "date": day_date.isoformat(), "status": day.status.value },
            ))

        if day.status not in (DayStatus.ScheduleApplies, DayStatus.NoOutages):
            continue

        published = before_status == DayStatus.WaitingForSchedule
        if not published and periods == before_periods and before_status == day.status:
            continue

        slots = [schedule_slot(start, end) for start, end in periods]
        events.append(PushEvent(
            topic       = SCHEDULE_CHANGES,
            dedup_key   = f"schedule:{queue}:{day_date.isoformat()}:{_slots_hash(periods)}",
            context     = {
                **common,
                "published": published,
                "slots": slots,
                "previous_slots": [schedule_slot(start, end) for start, end in before_periods],
            },
            summary     = {
                "queue": queue,
                "date": day_date.isoformat(),
                "slots": ", ".join(f"{s['start']}-{s['end']}" for s in slots) or "-",
            },
        ))

    return events


@dataclass
class _Outage:
    day_date: date
    start: datetime
    end: datetime
    start_minutes: int


def _outages(unit: UnitSchedule, tz: tzinfo) -> list[_Outage]:
    """Scheduled outages as absolute periods; an outage running over midnight stays one outage."""
    outages: list[_Outage] = []
    for day in sorted(unit.days, key=lambda d: local_date(d, tz)):
        if day.status != DayStatus.ScheduleApplies:
            continue
        day_date = local_date(day, tz)
        midnight = datetime.combine(day_date, time(), tzinfo=tz)
        for start, end in merge_slots(day):
            start_at = midnight + timedelta(minutes=start)
            end_at = midnight + timedelta(minutes=end)
            if outages and start_at <= outages[-1].end:
                outages[-1].end = max(outages[-1].end, end_at)
                continue
            outages.append(_Outage(day_date, start_at, end_at, start))
    return outages


def upcoming_events(unit: UnitSchedule, queue: str, tz: tzinfo, now: datetime, lead_minutes: int) -> list[PushEvent]:
    events: list[PushEvent] = []
    for outage in _outages(unit, tz):
        seconds_left = (outage.start - now).total_seconds()
        # An outage already in progress gets no reminder
        if not 0 < seconds_left <= lead_minutes * 60:
            continue
        end_minutes = outage.start_minutes + int((outage.end - outage.start).total_seconds() // 60)
        slot = schedule_slot(outage.start_minutes, end_minutes % MINUTES_PER_DAY or MINUTES_PER_DAY)
        slot["end_minutes"] = end_minutes
        events.append(PushEvent(
            topic       = OUTAGE_UPCOMING,
            dedup_key   = f"upcoming:{queue}:{outage.day_date.isoformat()}:{outage.start_minutes}",
            context     = {
                "queue": queue,
                "date": outage.day_date,
                "slot": slot,
                "minutes_left": math.ceil(seconds_left / 60),
            },
            summary     = { "queue": queue, "date": outage.day_date.isoformat(), "start": slot["start"] },
        ))
    return events


@inject
class SchedulePushTriggers:
    def __init__(
        self,
        dispatcher: PushEventDispatcher,
        templates: PushTemplatesService,
        dashboard: IDashboardRepository,
        outages: OutagesScheduleService,
    ):
        self._dispatcher = dispatcher
        self._templates = templates
        self._dashboard = dashboard
        self._outages = outages

    async def _get_queue(self) -> str | None:
        config = await self._dashboard.get_config()
        return config.outages_schedule_queue if config else None

    async def on_schedule_updated(self, update: ScheduleUpdate):
        queue = await self._get_queue()
        if not queue:
            return
        tz = self._templates.timezone
        today = datetime.now(tz).date()
        for event in schedule_events(update, queue, tz, today):
            await self._dispatcher.dispatch(event)

    async def check_upcoming(self, now: datetime | None = None):
        queue = await self._get_queue()
        if not queue:
            return
        schedule = await self._outages.get_schedule_async(queue)
        unit = schedule.root.get(queue) if schedule else None
        if not unit:
            return
        lead_minutes = await self._templates.get_param_value(OUTAGE_UPCOMING, LEAD_MINUTES)
        now = now or datetime.now(timezone.utc)
        for event in upcoming_events(unit, queue, self._templates.timezone, now, lead_minutes):
            await self._dispatcher.dispatch(event)
