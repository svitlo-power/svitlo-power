"""Tests for app/services/push/triggers."""
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from beanie import PydanticObjectId

from app.services.push.events import DEBOUNCE_SECONDS, HYSTERESIS, LEAD_MINUTES, THRESHOLD
from app.services.push.topics import EMERGENCY, OUTAGE_UPCOMING, SCHEDULE_CHANGES
from app.services.push.triggers.battery import BatteryPushTriggers
from app.services.push.triggers.power import PowerPushTriggers
from app.services.push.triggers.schedule import SchedulePushTriggers, merge_slots, schedule_events, upcoming_events
from shared.models.assumed_station_status import AssumedStationStatus
from shared.models.localizable_value import LocalizableValue
from shared.services.outages_schedule import ScheduleUpdate
from shared.services.outages_schedule.models import DaySchedule, DayStatus, SchedulesResponse, Slot, SlotType, UnitSchedule


KYIV = ZoneInfo("Europe/Kyiv")
TODAY = date(2026, 10, 22)
QUEUE = "1.1"


def _day(day_date: date, slots=(), status=DayStatus.ScheduleApplies) -> DaySchedule:
    return DaySchedule(
        date=datetime.combine(day_date, datetime.min.time(), tzinfo=KYIV),
        status=status,
        slots=[Slot(start=s, end=e, type=SlotType.Definite) for s, e in slots],
    )


def _schedule(*days: DaySchedule, queue=QUEUE) -> SchedulesResponse:
    return SchedulesResponse({queue: UnitSchedule(days=list(days), updatedOn=datetime.now(timezone.utc))})


def _events(previous, current):
    return schedule_events(ScheduleUpdate(previous=previous, current=current), QUEUE, KYIV, TODAY)


def _templates(params=None):
    params = params or {}
    templates = MagicMock()
    templates.timezone = KYIV
    templates.get_param_value = AsyncMock(side_effect=lambda topic, key: params[key])
    return templates


def _dispatcher():
    dispatcher = MagicMock()
    dispatcher.dispatch = AsyncMock()
    return dispatcher


def _dispatched(dispatcher):
    return [c.args[0] for c in dispatcher.dispatch.await_args_list]


class _States:
    def __init__(self, initial=None):
        self.items = dict(initial or {})

    async def get_state(self, key):
        return self.items.get(key)

    async def set_state(self, key, data):
        self.items[key] = data


class TestMergeSlots:
    def test_adjacent_slots_are_one_outage(self):
        day = _day(TODAY, [(600, 720), (480, 600), (900, 960)])
        assert merge_slots(day) == [(480, 720), (900, 960)]


class TestScheduleEvents:
    def test_first_fetch_is_baseline(self):
        assert _events(None, _schedule(_day(TODAY, [(480, 720)]))) == []

    def test_no_change_no_events(self):
        schedule = _schedule(_day(TODAY, [(480, 720)]))
        assert _events(schedule, _schedule(_day(TODAY, [(480, 720)]))) == []

    def test_split_slots_are_not_a_change(self):
        previous = _schedule(_day(TODAY, [(480, 720)]))
        current = _schedule(_day(TODAY, [(480, 600), (600, 720)]))
        assert _events(previous, current) == []

    def test_other_queue_change_is_ignored(self):
        same = _schedule(_day(TODAY, [(0, 60)])).root[QUEUE]
        previous = _schedule(_day(TODAY, [(480, 720)]), queue="2.1")
        current = _schedule(_day(TODAY, [(600, 720)]), queue="2.1")
        previous.root[QUEUE] = current.root[QUEUE] = same
        assert _events(previous, current) == []

    def test_changed_slots(self):
        previous = _schedule(_day(TODAY, [(480, 720)]))
        current = _schedule(_day(TODAY, [(600, 720)]))

        [event] = _events(previous, current)

        assert event.topic == SCHEDULE_CHANGES
        assert event.dedup_key.startswith(f"schedule:{QUEUE}:2026-10-22:")
        assert event.context["published"] is False
        assert event.context["day"] == "today"
        assert event.context["slots"] == [{"start": "10:00", "end": "12:00", "start_minutes": 600, "end_minutes": 720}]
        assert event.context["previous_slots"][0]["start"] == "08:00"

    def test_tomorrow_published(self):
        tomorrow = TODAY + timedelta(days=1)
        previous = _schedule(_day(TODAY), _day(tomorrow, status=DayStatus.WaitingForSchedule))
        current = _schedule(_day(TODAY), _day(tomorrow, [(480, 720)]))

        [event] = _events(previous, current)

        assert event.topic == SCHEDULE_CHANGES
        assert event.context["published"] is True
        assert event.context["day"] == "tomorrow"

    def test_new_day_appearing_published(self):
        tomorrow = TODAY + timedelta(days=1)
        previous = _schedule(_day(TODAY))
        current = _schedule(_day(TODAY), _day(tomorrow, status=DayStatus.NoOutages))

        [event] = _events(previous, current)

        assert event.context["published"] is True
        assert event.context["slots"] == []

    def test_new_day_still_waiting_is_silent(self):
        tomorrow = TODAY + timedelta(days=1)
        previous = _schedule(_day(TODAY))
        current = _schedule(_day(TODAY), _day(tomorrow, status=DayStatus.WaitingForSchedule))
        assert _events(previous, current) == []

    def test_same_slots_give_same_dedup_key(self):
        previous = _schedule(_day(TODAY, [(480, 720)]))
        first = _events(previous, _schedule(_day(TODAY, [(600, 720)])))
        second = _events(previous, _schedule(_day(TODAY, [(600, 720)])))
        assert first[0].dedup_key == second[0].dedup_key

    def test_emergency_started_and_ended(self):
        previous = _schedule(_day(TODAY, [(480, 720)]))
        emergency = _schedule(_day(TODAY, status=DayStatus.EmergencyShutdowns))

        [started] = _events(previous, emergency)
        assert started.topic == EMERGENCY
        assert started.context["active"] is True
        assert started.dedup_key == f"emergency:{QUEUE}:2026-10-22:EmergencyShutdowns"

        events = _events(emergency, _schedule(_day(TODAY, [(480, 720)])))
        ended = next(e for e in events if e.topic == EMERGENCY)
        assert ended.context["active"] is False
        assert ended.context["previous_status"] == "EmergencyShutdowns"
        assert ended.dedup_key == f"emergency:{QUEUE}:2026-10-22:ScheduleApplies"


class TestUpcoming:
    def _unit(self, *days):
        return _schedule(*days).root[QUEUE]

    def _at(self, hour, minute=0, day=TODAY):
        return datetime.combine(day, datetime.min.time(), tzinfo=KYIV).replace(hour=hour, minute=minute)

    def test_reminder_within_lead_time(self):
        unit = self._unit(_day(TODAY, [(14 * 60, 18 * 60)]))

        [event] = upcoming_events(unit, QUEUE, KYIV, self._at(13, 40), 30)

        assert event.topic == OUTAGE_UPCOMING
        assert event.dedup_key == f"upcoming:{QUEUE}:2026-10-22:840"
        assert event.context["minutes_left"] == 20
        assert event.context["slot"]["start"] == "14:00"
        assert event.context["slot"]["end"] == "18:00"

    @pytest.mark.parametrize("hour, minute", [(13, 20), (14, 0), (15, 0)])
    def test_no_reminder_too_early_or_in_progress(self, hour, minute):
        unit = self._unit(_day(TODAY, [(14 * 60, 18 * 60)]))
        assert upcoming_events(unit, QUEUE, KYIV, self._at(hour, minute), 30) == []

    def test_only_definite_schedule_days(self):
        unit = self._unit(_day(TODAY, [(14 * 60, 18 * 60)], status=DayStatus.EmergencyShutdowns))
        assert upcoming_events(unit, QUEUE, KYIV, self._at(13, 45), 30) == []

    def test_outage_over_midnight_is_not_reminded_again(self):
        tomorrow = TODAY + timedelta(days=1)
        unit = self._unit(_day(TODAY, [(22 * 60, 24 * 60)]), _day(tomorrow, [(0, 2 * 60)]))

        assert upcoming_events(unit, QUEUE, KYIV, self._at(23, 45), 30) == []
        [event] = upcoming_events(unit, QUEUE, KYIV, self._at(21, 45), 30)
        assert event.context["slot"]["end"] == "02:00"

    def test_moved_slot_gets_new_key(self):
        first = upcoming_events(self._unit(_day(TODAY, [(14 * 60, 18 * 60)])), QUEUE, KYIV, self._at(13, 45), 30)
        moved = upcoming_events(self._unit(_day(TODAY, [(14 * 60 + 30, 18 * 60)])), QUEUE, KYIV, self._at(14, 15), 30)
        assert first[0].dedup_key != moved[0].dedup_key


class TestSchedulePushTriggers:
    def _triggers(self, queue=QUEUE, schedule=None):
        dashboard = MagicMock()
        dashboard.get_config = AsyncMock(return_value=SimpleNamespace(outages_schedule_queue=queue))
        outages = MagicMock()
        outages.get_schedule_async = AsyncMock(return_value=schedule)
        dispatcher = _dispatcher()
        triggers = SchedulePushTriggers(dispatcher, _templates({LEAD_MINUTES: 30}), dashboard, outages)
        return triggers, dispatcher

    @pytest.mark.asyncio
    async def test_on_schedule_updated_dispatches_events(self):
        triggers, dispatcher = self._triggers()
        today = datetime.now(KYIV).date()
        update = ScheduleUpdate(
            previous=_schedule(_day(today, [(480, 720)])),
            current=_schedule(_day(today, [(600, 720)])),
        )

        await triggers.on_schedule_updated(update)

        assert [e.topic for e in _dispatched(dispatcher)] == [SCHEDULE_CHANGES]

    @pytest.mark.asyncio
    async def test_no_queue_configured(self):
        triggers, dispatcher = self._triggers(queue=None)
        await triggers.on_schedule_updated(ScheduleUpdate(previous=_schedule(), current=_schedule()))
        await triggers.check_upcoming()
        dispatcher.dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_upcoming_uses_lead_param(self):
        now = datetime.now(KYIV).replace(second=0, microsecond=0)
        start = now + timedelta(minutes=20)
        minutes = start.hour * 60 + start.minute
        if minutes + 60 > 24 * 60:
            pytest.skip("Too close to midnight for a same-day slot")
        triggers, dispatcher = self._triggers(schedule=_schedule(_day(start.date(), [(minutes, minutes + 60)])))

        await triggers.check_upcoming(now)

        [event] = _dispatched(dispatcher)
        assert event.topic == OUTAGE_UPCOMING


def _building(report_users=1, station=None, name=None):
    return SimpleNamespace(
        id=PydanticObjectId(),
        name=LocalizableValue(name or {"uk": "Будинок", "en": "Building"}),
        report_users=[SimpleNamespace(id=PydanticObjectId()) for _ in range(report_users)],
        station=station,
    )


class TestPowerTriggers:
    T0 = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)

    def _setup(self, building, debounce=60, states=None):
        reports = {}
        ext_data = MagicMock()
        ext_data.get_last_ext_data_by_user_id = AsyncMock(side_effect=lambda user_id: reports.get(user_id))
        dashboard = MagicMock()
        dashboard.get_buildings = AsyncMock(return_value=[building])
        dispatcher = _dispatcher()
        states = states or _States()
        triggers = PowerPushTriggers(dispatcher, _templates({DEBOUNCE_SECONDS: debounce}), dashboard, ext_data, states)

        def report(user_index, state, at):
            reports[building.report_users[user_index].id] = SimpleNamespace(grid_state=state, received_at=at)

        return triggers, dispatcher, report, states

    @pytest.mark.asyncio
    async def test_first_check_is_baseline(self):
        building = _building()
        triggers, dispatcher, report, states = self._setup(building)
        report(0, False, self.T0)

        await triggers.check(self.T0 + timedelta(minutes=5))

        dispatcher.dispatch.assert_not_called()
        assert states.items[f"power:{building.id}"] == {"confirmed": False}

    @pytest.mark.asyncio
    async def test_power_lost_after_debounce(self):
        building = _building()
        triggers, dispatcher, report, _ = self._setup(building)
        report(0, True, self.T0)
        await triggers.check(self.T0)

        lost_at = self.T0 + timedelta(minutes=1)
        report(0, False, lost_at)
        await triggers.check(lost_at + timedelta(seconds=15))
        dispatcher.dispatch.assert_not_called()

        await triggers.check(lost_at + timedelta(seconds=60))
        await triggers.check(lost_at + timedelta(seconds=75))

        [event] = _dispatched(dispatcher)
        assert event.context["available"] is False
        assert event.context["changed_at"] == lost_at.astimezone(KYIV)
        assert event.dedup_key == f"power:{building.id}:off:{lost_at.isoformat()}"
        assert event.data == {"buildingId": str(building.id)}
        assert event.building_id == building.id
        assert event.context["building"]["name"].root["en"] == "Building"

    @pytest.mark.asyncio
    async def test_short_flap_is_ignored(self):
        building = _building()
        triggers, dispatcher, report, states = self._setup(building)
        report(0, True, self.T0)
        await triggers.check(self.T0)

        report(0, False, self.T0 + timedelta(seconds=10))
        await triggers.check(self.T0 + timedelta(seconds=15))
        report(0, True, self.T0 + timedelta(seconds=40))
        await triggers.check(self.T0 + timedelta(seconds=45))
        await triggers.check(self.T0 + timedelta(minutes=5))

        dispatcher.dispatch.assert_not_called()
        assert states.items[f"power:{building.id}"] == {"confirmed": True}

    @pytest.mark.asyncio
    async def test_power_is_on_while_any_reporter_has_it(self):
        building = _building(report_users=2)
        triggers, dispatcher, report, _ = self._setup(building, debounce=0)
        report(0, True, self.T0)
        report(1, True, self.T0)
        await triggers.check(self.T0)

        report(0, False, self.T0 + timedelta(minutes=1))
        await triggers.check(self.T0 + timedelta(minutes=2))
        dispatcher.dispatch.assert_not_called()

        report(1, False, self.T0 + timedelta(minutes=3))
        await triggers.check(self.T0 + timedelta(minutes=3))
        [event] = _dispatched(dispatcher)
        assert event.context["available"] is False

    @pytest.mark.asyncio
    async def test_power_restored(self):
        building = _building()
        triggers, dispatcher, report, _ = self._setup(building, debounce=0)
        report(0, False, self.T0)
        await triggers.check(self.T0)

        report(0, True, self.T0 + timedelta(minutes=1))
        await triggers.check(self.T0 + timedelta(minutes=1))

        [event] = _dispatched(dispatcher)
        assert event.context["available"] is True
        assert ":on:" in event.dedup_key

    @pytest.mark.asyncio
    async def test_building_without_reports_is_skipped(self):
        building = _building(report_users=0)
        triggers, dispatcher, _, states = self._setup(building)

        await triggers.check(self.T0)

        assert states.items == {}

    @pytest.mark.asyncio
    async def test_failure_for_one_building_does_not_stop_others(self):
        broken, good = _building(), _building()
        ext_data = MagicMock()

        async def last(user_id):
            if user_id == broken.report_users[0].id:
                raise RuntimeError("db")
            return SimpleNamespace(grid_state=True, received_at=self.T0)
        ext_data.get_last_ext_data_by_user_id = AsyncMock(side_effect=last)
        dashboard = MagicMock()
        dashboard.get_buildings = AsyncMock(return_value=[broken, good])
        states = _States()
        triggers = PowerPushTriggers(_dispatcher(), _templates({DEBOUNCE_SECONDS: 0}), dashboard, ext_data, states)

        await triggers.check(self.T0)

        assert f"power:{good.id}" in states.items


class TestBatteryTriggers:
    def _setup(self, buildings, soc=50, offline=False, connection_status="NORMAL"):
        stations_data = MagicMock()
        stations_data.get_assumed_connection_status = AsyncMock(
            return_value=AssumedStationStatus.OFFLINE if offline else AssumedStationStatus.NORMAL
        )
        current = {"soc": soc}
        stations_data.get_last_station_data = AsyncMock(side_effect=lambda station_id: SimpleNamespace(
            battery_soc=current["soc"],
            last_update_time=datetime(2026, 10, 22, 10, 0) + timedelta(minutes=current.get("tick", 0)),
        ))
        dashboard = MagicMock()
        dashboard.get_buildings = AsyncMock(return_value=buildings)
        dispatcher = _dispatcher()
        states = _States()
        triggers = BatteryPushTriggers(
            dispatcher, _templates({THRESHOLD: 20, HYSTERESIS: 10}), dashboard, stations_data, states,
        )

        async def at(value):
            current["soc"] = value
            current["tick"] = current.get("tick", 0) + 1
            await triggers.check()

        return triggers, dispatcher, at

    @staticmethod
    def _station(**kwargs):
        values = dict(
            id=PydanticObjectId(), station_id=1, station_name="Deye", station_alias=None,
            enabled=True, connection_status="NORMAL",
        )
        values.update(kwargs)
        return SimpleNamespace(**values)

    @pytest.mark.asyncio
    async def test_fires_once_per_episode_and_rearms_after_hysteresis(self):
        station = self._station()
        building = _building(station=station)
        _, dispatcher, at = self._setup([building])

        await at(50)
        await at(20)   # low: fires
        await at(15)
        await at(25)   # above threshold but within hysteresis: still disarmed
        await at(19)
        assert dispatcher.dispatch.await_count == 1

        await at(31)   # above threshold + hysteresis: re-armed
        await at(18)   # new episode
        events = _dispatched(dispatcher)
        assert len(events) == 2
        assert events[0].dedup_key != events[1].dedup_key
        assert events[0].dedup_key.startswith(f"battery:{station.id}:")
        assert events[0].context["soc"] == 20
        assert events[0].context["threshold"] == 20
        assert events[0].data == {"buildingId": str(building.id), "stationId": str(station.id)}

    @pytest.mark.asyncio
    async def test_offline_station_is_skipped(self):
        _, dispatcher, at = self._setup([_building(station=self._station())], offline=True)
        await at(5)
        dispatcher.dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_all_offline_station_is_skipped(self):
        _, dispatcher, at = self._setup([_building(station=self._station(connection_status="ALL_OFFLINE"))])
        await at(5)
        dispatcher.dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_building_without_station_is_skipped(self):
        _, dispatcher, at = self._setup([_building(station=None)])
        await at(5)
        dispatcher.dispatch.assert_not_called()

    @pytest.mark.asyncio
    async def test_station_shared_by_buildings_fires_once(self):
        station = self._station()
        _, dispatcher, at = self._setup([_building(station=station), _building(station=station)])
        await at(5)
        assert dispatcher.dispatch.await_count == 1
