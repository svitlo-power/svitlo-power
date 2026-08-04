import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { StationConnectionsState, ServerStationConnectionItem } from "../types";
import {
  createStationConnection,
  deleteStationConnection,
  fetchStationConnections,
  saveStationConnection,
} from "../thunks";

const initialState: StationConnectionsState = {
  connections: [],
  error: null,
  loading: false,
};

export const stationConnectionsSlice = createSlice({
  name: 'stationConnections',
  initialState: initialState,
  reducers: {
    clearStationConnectionsError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchStationConnections.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchStationConnections.fulfilled, (state, action: PayloadAction<Array<ServerStationConnectionItem>>) => {
        state.connections = action.payload;
        state.loading = false;
      })
      .addCase(fetchStationConnections.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    [createStationConnection, saveStationConnection, deleteStationConnection].forEach(thunk => {
      builder
        .addCase(thunk.pending, (state) => {
          state.loading = true;
          state.error = null;
        })
        .addCase(thunk.fulfilled, (state) => {
          state.loading = false;
        })
        .addCase(thunk.rejected, (state, action) => {
          state.loading = false;
          state.error = action.payload as string;
        });
    });
  },
});

export const { clearStationConnectionsError } = stationConnectionsSlice.actions;
export const stationConnectionsReducer = stationConnectionsSlice.reducer;
