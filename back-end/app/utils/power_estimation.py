import logging

logger = logging.getLogger(__name__)

def get_kilowatthour_consumption(average_consumption_w: float, minutes: int):
    return average_consumption_w * minutes / 60000.0

def get_estimate_discharge_time(batt_capacity_kwh: float, batt_soc: int, average_consumption_kwh: float, target_batt_soc: int = 0):
    remaining_energy_kwh = batt_capacity_kwh * (batt_soc - target_batt_soc) / 100
    time_left = remaining_energy_kwh / average_consumption_kwh

    hours = int(time_left)
    minutes = int((time_left - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"

def get_estimate_charge_time(batt_capacity_kwh: float, current_batt_soc: int, charge_power_kw: float, target_batt_soc: int = 100):
    remaining_energy_kwh = batt_capacity_kwh * (target_batt_soc - current_batt_soc) / 100
    time_left = remaining_energy_kwh / charge_power_kw

    hours = int(time_left)
    minutes = int((time_left - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"