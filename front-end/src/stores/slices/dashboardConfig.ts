import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { DashboardConfig, DashboardConfigState } from "../types";
import { fetchDashboardConfig, saveDashboardConfig } from "../thunks/dashboardConfig";

const initialState: DashboardConfigState = {
  loading: false,
  error: null,
  changed: false,
};

export const dashboardConfigSlice = createSlice({
  name: 'dashboardConfig',
  initialState: initialState,
  reducers: {
    startEditingDashboardConfig(state) {
      state.editingConfig = state.config;
    },
    finishEditingDashboardConfig(state, { payload }: PayloadAction<DashboardConfig>) {
      state.config = payload;
      delete state.editingConfig;
      state.changed = true;
    },
    cancelEditingDashboardConfig(state) {
      delete state.editingConfig;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardConfig.fulfilled, (state, { payload }: PayloadAction<DashboardConfig>) => {
        state.config = { ...payload };
        state.loading = false;
      })
      .addCase(fetchDashboardConfig.rejected, (state, { payload }: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = payload as string;
      });
    builder
      .addCase(saveDashboardConfig.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(saveDashboardConfig.fulfilled, (state, { payload }: PayloadAction<DashboardConfig>) => {
        state.config = { ...payload };
        state.loading = false;
        state.changed = false;
      })
      .addCase(saveDashboardConfig.rejected, (state, { payload }: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = payload as string;
      });
  },
});

export const {
  startEditingDashboardConfig,
  finishEditingDashboardConfig,
  cancelEditingDashboardConfig,
} = dashboardConfigSlice.actions;
export const dashboardConfigReducer = dashboardConfigSlice.reducer;