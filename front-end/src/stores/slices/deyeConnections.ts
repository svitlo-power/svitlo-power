import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { DeyeConnectionsState, ServerDeyeConnectionItem } from "../types";
import {
  createDeyeConnection,
  deleteDeyeConnection,
  fetchDeyeConnections,
  saveDeyeConnection,
} from "../thunks";

const initialState: DeyeConnectionsState = {
  connections: [],
  error: null,
  loading: false,
};

export const deyeConnectionsSlice = createSlice({
  name: 'deyeConnections',
  initialState: initialState,
  reducers: {
    clearDeyeConnectionsError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDeyeConnections.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDeyeConnections.fulfilled, (state, action: PayloadAction<Array<ServerDeyeConnectionItem>>) => {
        state.connections = action.payload;
        state.loading = false;
      })
      .addCase(fetchDeyeConnections.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    [createDeyeConnection, saveDeyeConnection, deleteDeyeConnection].forEach(thunk => {
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

export const { clearDeyeConnectionsError } = deyeConnectionsSlice.actions;
export const deyeConnectionsReducer = deyeConnectionsSlice.reducer;
