import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { ServerStationItem, StationsState } from "../types";
import { fetchStations, saveStations } from "../thunks";
import { ObjectId } from "../../schemas";

const initialState: StationsState = {
  stations: [],
  error: null,
  loading: false,
};

export type UpdateStationActionPayload = {
  id: ObjectId;
  enabled: boolean;
};

export type UpdateStationBatteryCapacityActionPayload = {
  id: ObjectId;
  batteryCapacity: number;
};

export type ChangeStationOrderPayload = {
  currentOrder: number;
  delta: number;
};

export const stationsSlice = createSlice({
  name: 'stations',
  initialState: initialState,
  reducers: {
    updateStationState(state, { payload }: PayloadAction<UpdateStationActionPayload>) {
      const station = state.stations.find(s => s.id === payload.id);
      if (!station) {
        return;
      }
      if (station.enabled !== payload.enabled) {
        station.enabled = payload.enabled;
        station.changed = true;
      }
    },
    updateStationBatteryCapacity(state, { payload }: PayloadAction<UpdateStationBatteryCapacityActionPayload>) {
      const station = state.stations.find(s => s.id === payload.id);
      if (!station) {
        return;
      }
      if (station.batteryCapacity !== payload.batteryCapacity) {
        station.batteryCapacity = payload.batteryCapacity;
        station.changed = true;
      }
    },
    updateStationOrder(state, { payload }: PayloadAction<ChangeStationOrderPayload>) {
      const { currentOrder, delta } = payload;
      const newOrder = currentOrder + delta;
      if (newOrder < 1 || newOrder > state.stations.length) {
        return;
      }

      const stationsCopy = [...state.stations];

      const stationA = state.stations[currentOrder - 1];
      const stationB = state.stations[newOrder - 1];

      stationsCopy[newOrder - 1] = { ...stationA, order: newOrder, changed: true };
      stationsCopy[currentOrder - 1] = { ...stationB, order: currentOrder, changed: true };

      state.stations = stationsCopy;
    },
    stationStateSaved(state, { payload: stationId }: PayloadAction<string>) {
      const station = state.stations.find(s => s.id === stationId);
      if (station) {
        station.changed = false;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchStations.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStations.fulfilled, (state, action: PayloadAction<Array<ServerStationItem>>) => {
        state.stations = action.payload.map(station => ({ ...station, changed: false}));
        state.loading = false;
      })
      .addCase(fetchStations.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
    builder
      .addCase(saveStations.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(saveStations.fulfilled, (state) => {
        state.loading = false;
      })
      .addCase(saveStations.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});
  
export const {
  updateStationState,
  updateStationOrder,
  updateStationBatteryCapacity,
  stationStateSaved,
} = stationsSlice.actions;
export const stationsReducer = stationsSlice.reducer;