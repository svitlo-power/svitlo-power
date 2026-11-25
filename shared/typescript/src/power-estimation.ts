/**
 * Port of `shared/python/shared/utils/power_estimation.py`.
 *
 * The string formatting is part of the published snapshot contract, so the
 * arithmetic and `HH:MM` formatting must stay bit-identical to the Python
 * producer.
 */

export const DEFAULT_DISCHARGE_TARGET_SOC = 10;
export const DEFAULT_CHARGE_TARGET_SOC = 97;

export interface PowerEstimationStation {
  discharge_target_soc?: number | null;
  charge_target_soc?: number | null;
}

export interface PowerEstimationSettings {
  getInt(key: string, fallback: number): Promise<number> | number;
}

/**
 * Resolves the discharge target SOC: station override first, then the
 * `discharge_target_soc` setting, then 10.
 */
export async function getDischargeTargetSoc(
  station?: PowerEstimationStation | null,
  settings?: PowerEstimationSettings | null,
): Promise<number> {
  if (
    station &&
    station.discharge_target_soc !== null &&
    station.discharge_target_soc !== undefined
  ) {
    return station.discharge_target_soc;
  }
  if (settings) {
    return await settings.getInt(
      "discharge_target_soc",
      DEFAULT_DISCHARGE_TARGET_SOC,
    );
  }
  return DEFAULT_DISCHARGE_TARGET_SOC;
}

/** Resolves the charge target SOC: station override first, then setting, then 97. */
export async function getChargeTargetSoc(
  station?: PowerEstimationStation | null,
  settings?: PowerEstimationSettings | null,
): Promise<number> {
  if (
    station &&
    station.charge_target_soc !== null &&
    station.charge_target_soc !== undefined
  ) {
    return station.charge_target_soc;
  }
  if (settings) {
    return await settings.getInt(
      "charge_target_soc",
      DEFAULT_CHARGE_TARGET_SOC,
    );
  }
  return DEFAULT_CHARGE_TARGET_SOC;
}

export function getKilowatthourConsumption(
  averageConsumptionW: number,
  minutes: number,
): number {
  return (averageConsumptionW * minutes) / 60_000;
}

/**
 * Python's `int()` truncates toward zero; `Math.trunc` matches it for both
 * signs, unlike `Math.floor`.
 */
function formatHoursMinutes(timeLeft: number): string {
  const hours = Math.trunc(timeLeft);
  const minutes = Math.trunc((timeLeft - hours) * 60);
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

export async function getEstimateDischargeTime(
  battCapacityKwh: number,
  battSoc: number,
  averageConsumptionKwh: number,
  targetBattSoc?: number | null,
  station?: PowerEstimationStation | null,
  settings?: PowerEstimationSettings | null,
): Promise<string> {
  const target =
    targetBattSoc === undefined || targetBattSoc === null
      ? await getDischargeTargetSoc(station, settings)
      : targetBattSoc;

  if (averageConsumptionKwh === 0) return "00:00";

  const remainingEnergyKwh = (battCapacityKwh * (battSoc - target)) / 100;
  const timeLeft = remainingEnergyKwh / averageConsumptionKwh;
  return formatHoursMinutes(timeLeft);
}

export async function getEstimateChargeTime(
  battCapacityKwh: number,
  currentBattSoc: number,
  chargePowerKw: number,
  targetBattSoc?: number | null,
  station?: PowerEstimationStation | null,
  settings?: PowerEstimationSettings | null,
): Promise<string> {
  const target =
    targetBattSoc === undefined || targetBattSoc === null
      ? await getChargeTargetSoc(station, settings)
      : targetBattSoc;

  if (chargePowerKw === 0) return "00:00";

  const remainingEnergyKwh =
    (battCapacityKwh * (target - currentBattSoc)) / 100;
  const timeLeft = remainingEnergyKwh / chargePowerKw;
  return formatHoursMinutes(timeLeft);
}
