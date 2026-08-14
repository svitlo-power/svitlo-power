"""Tests for app/utils/power_estimation.py."""
from app.utils.power_estimation import (
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
    def test_basic_calculation(self):
        result = get_estimate_discharge_time(10.0, 100, 1.0)
        assert result == "10:00"

    def test_with_target_soc(self):
        result = get_estimate_discharge_time(10.0, 100, 1.0, target_batt_soc=50)
        assert result == "05:00"

    def test_zero_consumption(self):
        result = get_estimate_discharge_time(10.0, 100, 0.0)
        assert result == "00:00"

    def test_full_discharge(self):
        result = get_estimate_discharge_time(10.0, 100, 2.0)
        assert result == "05:00"

    def test_fractional_hours(self):
        result = get_estimate_discharge_time(10.0, 100, 3.0)
        assert result == "03:20"

    def test_zero_soc(self):
        result = get_estimate_discharge_time(10.0, 0, 1.0)
        assert result == "00:00"


class TestGetEstimateChargeTime:
    def test_basic_calculation(self):
        result = get_estimate_charge_time(10.0, 0, 1.0)
        assert result == "10:00"

    def test_with_target_soc(self):
        result = get_estimate_charge_time(10.0, 0, 1.0, target_batt_soc=50)
        assert result == "05:00"

    def test_zero_charge_power(self):
        result = get_estimate_charge_time(10.0, 0, 0.0)
        assert result == "00:00"

    def test_full_charge(self):
        result = get_estimate_charge_time(10.0, 0, 2.0)
        assert result == "05:00"

    def test_fractional_hours(self):
        result = get_estimate_charge_time(10.0, 0, 3.0)
        assert result == "03:20"

    def test_already_at_target(self):
        result = get_estimate_charge_time(10.0, 100, 1.0)
        assert result == "00:00"
