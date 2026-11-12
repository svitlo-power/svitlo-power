"""Tests for shared/utils/power_estimation.py."""
from unittest.mock import MagicMock

import pytest
from shared.utils.power_estimation import (
    get_kilowatthour_consumption,
    get_estimate_discharge_time,
    get_estimate_charge_time,
)


class TestGetKilowatthourConsumption:
    def test_basic_calculation(self):
        result = get_kilowatthour_consumption(1000, 60)
        assert result == 1.0

    def test_zero_consumption(self):
        result = get_kilowatthour_consumption(0, 60)
        assert result == 0.0

    def test_zero_minutes(self):
        result = get_kilowatthour_consumption(1000, 0)
        assert result == 0.0

    def test_fractional_result(self):
        result = get_kilowatthour_consumption(500, 30)
        assert result == 0.25

    def test_large_values(self):
        result = get_kilowatthour_consumption(5000, 120)
        assert result == 10.0


class TestGetEstimateDischargeTime:
    @pytest.mark.asyncio
    async def test_basic_calculation(self):
        # Use target_soc=0 to match original behavior (discharge to 0%)
        result = await get_estimate_discharge_time(10.0, 100, 1.0, target_batt_soc=0)
        assert result == "10:00"

    @pytest.mark.asyncio
    async def test_with_target_soc(self):
        result = await get_estimate_discharge_time(10.0, 100, 1.0, target_batt_soc=50)
        assert result == "05:00"

    @pytest.mark.asyncio
    async def test_zero_consumption(self):
        result = await get_estimate_discharge_time(10.0, 100, 0.0)
        assert result == "00:00"

    @pytest.mark.asyncio
    async def test_full_discharge(self):
        # Use target_soc=0 to match original behavior
        result = await get_estimate_discharge_time(10.0, 100, 2.0, target_batt_soc=0)
        assert result == "05:00"

    @pytest.mark.asyncio
    async def test_fractional_hours(self):
        # Use target_soc=0 to match original behavior
        result = await get_estimate_discharge_time(10.0, 100, 3.0, target_batt_soc=0)
        assert result == "03:20"

    @pytest.mark.asyncio
    async def test_zero_soc(self):
        # Use target_soc=0 to match original behavior
        result = await get_estimate_discharge_time(10.0, 0, 1.0, target_batt_soc=0)
        assert result == "00:00"


class TestGetEstimateChargeTime:
    @pytest.mark.asyncio
    async def test_basic_calculation(self):
        # Use target_soc=100 to match original behavior (charge to 100%)
        result = await get_estimate_charge_time(10.0, 0, 1.0, target_batt_soc=100)
        assert result == "10:00"

    @pytest.mark.asyncio
    async def test_with_target_soc(self):
        result = await get_estimate_charge_time(10.0, 0, 1.0, target_batt_soc=50)
        assert result == "05:00"

    @pytest.mark.asyncio
    async def test_zero_charge_power(self):
        result = await get_estimate_charge_time(10.0, 0, 0.0)
        assert result == "00:00"

    @pytest.mark.asyncio
    async def test_full_charge(self):
        # Use target_soc=100 to match original behavior
        result = await get_estimate_charge_time(10.0, 0, 2.0, target_batt_soc=100)
        assert result == "05:00"

    @pytest.mark.asyncio
    async def test_fractional_hours(self):
        # Use target_soc=100 to match original behavior
        result = await get_estimate_charge_time(10.0, 0, 3.0, target_batt_soc=100)
        assert result == "03:20"

    @pytest.mark.asyncio
    async def test_already_at_target(self):
        # Use target_soc=100 to match original behavior
        result = await get_estimate_charge_time(10.0, 100, 1.0, target_batt_soc=100)
        assert result == "00:00"


class TestGetEstimateDischargeTimeStationOverride:
    """Tests that station-level discharge_target_soc overrides the global setting."""

    def _station(self, discharge_target_soc):
        station = MagicMock()
        station.discharge_target_soc = discharge_target_soc
        return station

    @pytest.mark.asyncio
    async def test_uses_station_override_when_set(self):
        station = self._station(30)
        # 10 kWh * (100 - 30) / 100 = 7 kWh remaining; / 1 kWh = 7 hours
        result = await get_estimate_discharge_time(10.0, 100, 1.0, station=station)
        assert result == "07:00"

    @pytest.mark.asyncio
    async def test_uses_station_override_when_zero(self):
        station = self._station(0)
        result = await get_estimate_discharge_time(10.0, 100, 1.0, station=station)
        assert result == "10:00"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_when_station_override_is_none(self):
        station = self._station(None)
        # No settings service in tests → default discharge target = 10
        # 10 kWh * (100 - 10) / 100 = 9 kWh remaining; / 1 kWh = 9 hours
        result = await get_estimate_discharge_time(10.0, 100, 1.0, station=station)
        assert result == "09:00"


class TestGetEstimateChargeTimeStationOverride:
    """Tests that station-level charge_target_soc overrides the global setting."""

    def _station(self, charge_target_soc):
        station = MagicMock()
        station.charge_target_soc = charge_target_soc
        return station

    @pytest.mark.asyncio
    async def test_uses_station_override_when_set(self):
        station = self._station(80)
        # 10 kWh * (80 - 0) / 100 = 8 kWh remaining; / 1 kW = 8 hours
        result = await get_estimate_charge_time(10.0, 0, 1.0, station=station)
        assert result == "08:00"

    @pytest.mark.asyncio
    async def test_uses_station_override_when_100(self):
        station = self._station(100)
        result = await get_estimate_charge_time(10.0, 0, 1.0, station=station)
        assert result == "10:00"

    @pytest.mark.asyncio
    async def test_falls_back_to_default_when_station_override_is_none(self):
        station = self._station(None)
        # No settings service in tests → default charge target = 97
        # 10 kWh * (97 - 0) / 100 = 9.7 kWh remaining; / 1 kW = 9.7 hours
        result = await get_estimate_charge_time(10.0, 0, 1.0, station=station)
        assert result == "09:41"
