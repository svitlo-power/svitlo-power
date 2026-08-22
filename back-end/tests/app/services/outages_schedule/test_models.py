"""Tests for app/services/outages_schedule/models.py."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.services.outages_schedule.models import (
    SlotType,
    DayStatus,
    Slot,
    DaySchedule,
    UnitSchedule,
    SchedulesResponse,
    keep_only_definite_slots,
)


class TestSlotType:
    def test_definite_value(self):
        assert SlotType.Definite.value == "Definite"

    def test_not_planned_value(self):
        assert SlotType.NotPlanned.value == "NotPlanned"

    def test_is_str_enum(self):
        assert isinstance(SlotType.Definite, str)


class TestDayStatus:
    def test_schedule_applies_value(self):
        assert DayStatus.ScheduleApplies.value == "ScheduleApplies"

    def test_emergency_shutdowns_value(self):
        assert DayStatus.EmergencyShutdowns.value == "EmergencyShutdowns"

    def test_waiting_for_schedule_value(self):
        assert DayStatus.WaitingForSchedule.value == "WaitingForSchedule"

    def test_no_outages_value(self):
        assert DayStatus.NoOutages.value == "NoOutages"


class TestSlot:
    def test_valid_slot(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        assert slot.start == 0
        assert slot.end == 120
        assert slot.type == SlotType.Definite

    def test_missing_start_raises_error(self):
        with pytest.raises(ValidationError):
            Slot(end=120, type=SlotType.Definite)

    def test_missing_end_raises_error(self):
        with pytest.raises(ValidationError):
            Slot(start=0, type=SlotType.Definite)

    def test_missing_type_raises_error(self):
        with pytest.raises(ValidationError):
            Slot(start=0, end=120)


class TestDaySchedule:
    def test_valid_day_schedule(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot], date=now, status=DayStatus.ScheduleApplies)
        assert len(day.slots) == 1
        assert day.date == now
        assert day.status == DayStatus.ScheduleApplies

    def test_missing_slots_raises_error(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            DaySchedule(date=now, status=DayStatus.ScheduleApplies)

    def test_missing_date_raises_error(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        with pytest.raises(ValidationError):
            DaySchedule(slots=[slot], status=DayStatus.ScheduleApplies)

    def test_missing_status_raises_error(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            DaySchedule(slots=[slot], date=now)


class TestUnitSchedule:
    def test_valid_unit_schedule(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot], date=now, status=DayStatus.ScheduleApplies)
        unit = UnitSchedule(days=[day], updatedOn=now)
        assert len(unit.days) == 1
        assert unit.updatedOn == now

    def test_missing_days_raises_error(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            UnitSchedule(updatedOn=now)

    def test_missing_updated_on_raises_error(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot], date=now, status=DayStatus.ScheduleApplies)
        with pytest.raises(ValidationError):
            UnitSchedule(days=[day])


class TestKeepOnlyDefiniteSlots:
    def test_filters_non_definite_slots(self):
        slot1 = Slot(start=0, end=120, type=SlotType.Definite)
        slot2 = Slot(start=120, end=240, type=SlotType.NotPlanned)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot1, slot2], date=now, status=DayStatus.ScheduleApplies)
        unit = UnitSchedule(days=[day], updatedOn=now)
        schedule = SchedulesResponse.model_validate({"queue1": unit})

        result = keep_only_definite_slots(schedule)
        assert len(result.root["queue1"].days[0].slots) == 1
        assert result.root["queue1"].days[0].slots[0].type == SlotType.Definite

    def test_keeps_all_definite_slots(self):
        slot1 = Slot(start=0, end=120, type=SlotType.Definite)
        slot2 = Slot(start=120, end=240, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot1, slot2], date=now, status=DayStatus.ScheduleApplies)
        unit = UnitSchedule(days=[day], updatedOn=now)
        schedule = SchedulesResponse.model_validate({"queue1": unit})

        result = keep_only_definite_slots(schedule)
        assert len(result.root["queue1"].days[0].slots) == 2


class TestSchedulesResponse:
    def test_valid_response(self):
        slot = Slot(start=0, end=120, type=SlotType.Definite)
        now = datetime.now(timezone.utc)
        day = DaySchedule(slots=[slot], date=now, status=DayStatus.ScheduleApplies)
        unit = UnitSchedule(days=[day], updatedOn=now)
        schedule = SchedulesResponse.model_validate({"queue1": unit})
        assert "queue1" in schedule.root
        assert len(schedule.root["queue1"].days) == 1

    def test_empty_response(self):
        schedule = SchedulesResponse.model_validate({})
        assert schedule.root == {}
