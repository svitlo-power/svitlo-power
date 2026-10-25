import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectStations = (state: RootState) => state.stations.stations;

export const selectStationsChanged = createSelector(
  [selectStations],
  (stations) => stations.some((station) => station.changed),
);

export const selectStationsMaxOrder = createSelector(
  [selectStations],
  (stations) => Math.max(...stations.map((station) => station.order)),
);
