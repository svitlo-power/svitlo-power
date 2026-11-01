"""Tests for dashboard snapshot models."""

from datetime import datetime, timezone
import pytest

from app.services.dashboard_snapshot.models import (
    DashboardSnapshot,
    BuildingSnapshot,
    ConfigSnapshot,
    UnitScheduleSnapshot,
    DayScheduleSnapshot,
    SlotSnapshot,
)


class TestSlotSnapshot:
    def test_valid_slot(self):
        slot = SlotSnapshot(start=0, end=60, type="Definite")
        assert slot.start == 0
        assert slot.end == 60
        assert slot.type == "Definite"

    def test_not_planned_slot(self):
        slot = SlotSnapshot(start=60, end=120, type="NotPlanned")
        assert slot.type == "NotPlanned"


class TestDayScheduleSnapshot:
    def test_valid_day(self):
        day = DayScheduleSnapshot(
            slots=[SlotSnapshot(start=0, end=60, type="Definite")],
            date=datetime(2026, 10, 31, tzinfo=timezone.utc),
            status="ScheduleApplies",
        )
        assert len(day.slots) == 1
        assert day.status == "ScheduleApplies"


class TestUnitScheduleSnapshot:
    def test_valid_unit_schedule(self):
        unit = UnitScheduleSnapshot(
            days=[
                DayScheduleSnapshot(
                    slots=[SlotSnapshot(start=0, end=60, type="Definite")],
                    date=datetime(2026, 10, 31, tzinfo=timezone.utc),
                    status="ScheduleApplies",
                )
            ],
            updatedOn=datetime(2026, 10, 31, tzinfo=timezone.utc),
        )
        assert len(unit.days) == 1


class TestBuildingSnapshot:
    def test_valid_building(self):
        building = BuildingSnapshot(
            id="507f1f77bcf86cd799439011",
            name={"uk": "Будинок", "en": "Building"},
            color="#FF0000",
            order=1,
            has_bound_station=True,
            is_grid_available=True,
            grid_availability_pct=100,
            has_mixed_reporter_states=False,
            is_charging=False,
            is_discharging=True,
            is_offline=False,
            battery_percent=85.5,
            consumption_power="1.23",
            battery_discharge_time="5:00",
            battery_charge_time="3:00",
            charge_source="Grid",
            charge_power=2.5,
        )
        assert building.id == "507f1f77bcf86cd799439011"
        assert building.has_bound_station is True
        assert building.battery_percent == 85.5
        assert building.name == {"uk": "Будинок", "en": "Building"}

    def test_invalid_id_rejected(self):
        with pytest.raises(ValueError):
            BuildingSnapshot(
                id="invalid-id",
                name={"uk": "Будинок", "en": "Building"},
                color="#FF0000",
                order=1,
                has_bound_station=False,
                charge_source="None",
            )


class TestConfigSnapshot:
    def test_valid_config(self):
        config = ConfigSnapshot(
            title={"uk": "Панель", "en": "Dashboard"},
            outages_schedule={
                "enable": True,
                "region_id": 25,
                "dso_id": 902,
                "queue": "queue1",
            },
        )
        assert config.title == {"uk": "Панель", "en": "Dashboard"}
        assert config.outages_schedule["enable"] is True

    def test_config_without_schedule(self):
        config = ConfigSnapshot(
            title={"uk": "Панель", "en": "Dashboard"},
            outages_schedule=None,
        )
        assert config.outages_schedule is None


class TestDashboardSnapshot:
    def test_valid_snapshot(self):
        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[
                BuildingSnapshot(
                    id="507f1f77bcf86cd799439011",
                    name={"uk": "Будинок", "en": "Building"},
                    color="#FF0000",
                    order=1,
                    has_bound_station=False,
                    charge_source="None",
                )
            ],
            config=ConfigSnapshot(
                title={"uk": "Панель", "en": "Dashboard"},
                outages_schedule=None,
            ),
            outages_schedules={},
        )
        assert snapshot.epoch == 1700000000000
        assert snapshot.version == 1
        assert len(snapshot.buildings) == 1

    def test_snapshot_serialization(self):
        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[],
            config=ConfigSnapshot(
                title={"uk": "Панель", "en": "Dashboard"},
                outages_schedule=None,
            ),
            outages_schedules={},
        )
        data = snapshot.model_dump(by_alias=True)
        assert data["epoch"] == 1700000000000
        assert data["version"] == 1
        assert data["generatedAt"] == datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc)

    def test_snapshot_json_serialization(self):
        snapshot = DashboardSnapshot(
            epoch=1700000000000,
            version=1,
            generated_at=datetime(2026, 10, 31, 18, 0, 0, tzinfo=timezone.utc),
            buildings=[],
            config=ConfigSnapshot(
                title={"uk": "Панель", "en": "Dashboard"},
                outages_schedule=None,
            ),
            outages_schedules={},
        )
        json_str = snapshot.model_dump_json()
        assert "1700000000000" in json_str
        assert "cache:dashboard" not in json_str
