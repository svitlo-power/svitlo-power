import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global settings service instance (will be set during app initialization)
_settings_service = None


def set_settings_service(service):
    """Set the settings service instance."""
    global _settings_service
    _settings_service = service


async def get_discharge_target_soc() -> int:
    """Get discharge target SOC from settings."""
    if _settings_service:
        return await _settings_service.get_int("discharge_target_soc", 10)
    return 10


async def get_charge_target_soc() -> int:
    """Get charge target SOC from settings."""
    if _settings_service:
        return await _settings_service.get_int("charge_target_soc", 97)
    return 97


def get_kilowatthour_consumption(average_consumption_w: float, minutes: int):
    return average_consumption_w * minutes / 60000.0


async def get_estimate_discharge_time(
    batt_capacity_kwh: float,
    batt_soc: int,
    average_consumption_kwh: float,
    target_batt_soc: Optional[int] = None,
) -> str:
    if target_batt_soc is None:
        target_batt_soc = await get_discharge_target_soc()
    
    if average_consumption_kwh == 0:
        return "00:00"

    remaining_energy_kwh = batt_capacity_kwh * (batt_soc - target_batt_soc) / 100
    time_left = remaining_energy_kwh / average_consumption_kwh

    hours = int(time_left)
    minutes = int((time_left - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"


async def get_estimate_charge_time(
    batt_capacity_kwh: float,
    current_batt_soc: int,
    charge_power_kw: float,
    target_batt_soc: Optional[int] = None,
) -> str:
    if target_batt_soc is None:
        target_batt_soc = await get_charge_target_soc()
    
    if charge_power_kw == 0:
        return "00:00"

    remaining_energy_kwh = batt_capacity_kwh * (target_batt_soc - current_batt_soc) / 100
    time_left = remaining_energy_kwh / charge_power_kw

    hours = int(time_left)
    minutes = int((time_left - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"