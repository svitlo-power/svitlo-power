"""Tests for app/models/api/dashboard.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import (
    SaveDashboardConfigRequest,
    DashboardConfigResponse,
    BuildingResponse,
    SaveBuildingRequest,
    EditBuildingResponse,
    PowerLogsRequest,
    BuildingsSummaryRequest,
    ChargeSource,
    BuildingSummaryResponse,
)
from shared.models.localizable_value import LocalizableValue


class TestSaveDashboardConfigRequest:
    def test_valid_request(self):
        title = LocalizableValue({"en": "My Dashboard", "uk": "Мій Панель"})
        req = SaveDashboardConfigRequest(
            title=title,
            enableOutagesSchedule=True,
            outagesScheduleQueue="queue1",
        )
        assert req.title.root == {"en": "My Dashboard", "uk": "Мій Панель"}
        assert req.enable_outages_schedule is True
        assert req.outages_schedule_queue == "queue1"

    def test_defaults(self):
        title = LocalizableValue({"en": "Test"})
        req = SaveDashboardConfigRequest(title=title)
        assert req.enable_outages_schedule is False
        assert req.outages_schedule_queue is None


class TestDashboardConfigResponse:
    def test_inherits_from_request(self):
        title = LocalizableValue({"en": "Test"})
        resp = DashboardConfigResponse(title=title)
        assert resp.title.root == {"en": "Test"}


class TestBuildingResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        name = LocalizableValue({"en": "Building 1"})
        resp = BuildingResponse(
            id=oid,
            name=name,
            color="#FF0000",
            hasBoundStation=True,
            order=1,
        )
        assert resp.id == oid
        assert resp.name.root == {"en": "Building 1"}
        assert resp.color == "#FF0000"
        assert resp.has_bound_station is True
        assert resp.order == 1


class TestSaveBuildingRequest:
    def test_valid_request(self):
        name = LocalizableValue({"en": "Building 1"})
        req = SaveBuildingRequest(
            name=name,
            color="#FF0000",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=1,
        )
        assert req.name.root == {"en": "Building 1"}
        assert req.color == "#FF0000"
        assert req.enabled is True
        assert req.order == 1


class TestEditBuildingResponse:
    def test_inherits_from_save_request(self):
        name = LocalizableValue({"en": "Building 1"})
        resp = EditBuildingResponse(
            name=name,
            color="#FF0000",
            stationId=None,
            reportUserIds=[],
            enabled=True,
            order=1,
        )
        assert resp.name.root == {"en": "Building 1"}


class TestPowerLogsRequest:
    def test_valid_request(self):
        req = PowerLogsRequest(startDate="2024-01-01", endDate="2024-01-31")
        assert req.start_date == "2024-01-01"
        assert req.end_date == "2024-01-31"

    def test_defaults(self):
        req = PowerLogsRequest()
        assert req.start_date is None
        assert req.end_date is None


class TestBuildingsSummaryRequest:
    def test_valid_request(self):
        oid = PydanticObjectId()
        req = BuildingsSummaryRequest(buildingIds=[oid])
        assert len(req.building_ids) == 1
        assert req.building_ids[0] == oid

    def test_missing_building_ids_raises_error(self):
        with pytest.raises(ValidationError):
            BuildingsSummaryRequest()


class TestChargeSource:
    def test_none_value(self):
        assert ChargeSource.NONE.value == "None"

    def test_grid_value(self):
        assert ChargeSource.GRID.value == "Grid"

    def test_generator_value(self):
        assert ChargeSource.GENERATOR.value == "Generator"

    def test_solar_value(self):
        assert ChargeSource.SOLAR.value == "Solar"

    def test_recuperation_value(self):
        assert ChargeSource.RECUPERATION.value == "Recuperation"


class TestBuildingSummaryResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        resp = BuildingSummaryResponse(
            id=oid,
            isGridAvailable=True,
            gridAvailabilityPct=85,
            hasMixedReporterStates=False,
            isCharging=True,
            isDischarging=False,
            isOffline=False,
            batteryPercent=75.5,
            consumptionPower="2.50",
            batteryDischargeTime="05:30",
            batteryChargeTime="02:00",
            chargeSource=ChargeSource.GRID,
            chargePower=3000.0,
        )
        assert resp.id == oid
        assert resp.is_grid_available is True
        assert resp.grid_availability_pct == 85
        assert resp.battery_percent == 75.5
        assert resp.consumption_power == "2.50"
        assert resp.charge_source == ChargeSource.GRID
        assert resp.charge_power == 3000.0

    def test_defaults(self):
        oid = PydanticObjectId()
        resp = BuildingSummaryResponse(id=oid)
        assert resp.is_grid_available is None
        assert resp.grid_availability_pct is None
        assert resp.charge_source == ChargeSource.NONE
