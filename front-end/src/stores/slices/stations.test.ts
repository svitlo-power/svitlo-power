import { stationsReducer, updateStationSoc } from "./stations";

const station = {
  id: "station-1" as const,
  stationName: "Test Station",
  stationAlias: { en: "TS", uk: "ТС" },
  connectionStatus: "online",
  gridInterconnectionType: "grid",
  lastUpdateTime: new Date(),
  connectionName: null,
  batteryCapacity: 10,
  dischargeTargetSoc: null,
  chargeTargetSoc: null,
  enabled: true,
  order: 1,
  changed: false,
};

describe("stations slice", () => {
  it("updates station SOC overrides and marks the station changed", () => {
    const state = stationsReducer(
      { stations: [station], loading: false, error: null },
      updateStationSoc({
        id: "station-1",
        dischargeTargetSoc: 30,
        chargeTargetSoc: 80,
      }),
    );

    expect(state.stations[0].dischargeTargetSoc).toBe(30);
    expect(state.stations[0].chargeTargetSoc).toBe(80);
    expect(state.stations[0].changed).toBe(true);
  });

  it("does not mark the station changed when SOC values are unchanged", () => {
    const initial = {
      ...station,
      dischargeTargetSoc: 30,
      chargeTargetSoc: 80,
      changed: false,
    };
    const state = stationsReducer(
      { stations: [initial], loading: false, error: null },
      updateStationSoc({
        id: "station-1",
        dischargeTargetSoc: 30,
        chargeTargetSoc: 80,
      }),
    );

    expect(state.stations[0].changed).toBe(false);
  });

  it("clears an override when set to null", () => {
    const initial = {
      ...station,
      dischargeTargetSoc: 30,
      chargeTargetSoc: 80,
      changed: false,
    };
    const state = stationsReducer(
      { stations: [initial], loading: false, error: null },
      updateStationSoc({
        id: "station-1",
        dischargeTargetSoc: null,
        chargeTargetSoc: null,
      }),
    );

    expect(state.stations[0].dischargeTargetSoc).toBeNull();
    expect(state.stations[0].chargeTargetSoc).toBeNull();
    expect(state.stations[0].changed).toBe(true);
  });

  it("does nothing when the station is not found", () => {
    const state = stationsReducer(
      { stations: [station], loading: false, error: null },
      updateStationSoc({
        id: "missing",
        dischargeTargetSoc: 30,
        chargeTargetSoc: 80,
      }),
    );

    expect(state.stations[0]).toEqual(station);
    expect(state.stations[0].changed).toBe(false);
  });
});
