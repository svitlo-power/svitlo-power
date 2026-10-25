import { createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";
import { DashboardConfig } from "../types";
import { RootState } from "../store";
import { toDashboardEditConfig } from "../../schemas/dashboardEdit";

const normalizeDashboardConfig = (config: DashboardConfig) => {
  const normalized = toDashboardEditConfig(config);
  return {
    title: normalized.title,
    outagesSchedule: normalized.outagesSchedule.enable ? normalized.outagesSchedule : null,
  };
};

export const fetchDashboardConfig = createAsyncThunk<DashboardConfig>('dashboardConfig/fetchDashboardConfig', async (_, thunkAPI) => {
  try {
    const response = await apiClient.get<DashboardConfig>('/dashboard/config');
    return normalizeDashboardConfig(response.data);
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch dashboard config');
  }
});

export const saveDashboardConfig = createAsyncThunk('dashboardConfig/updateDashboardConfig', async (_, thunkAPI) => {
  try {
    const state = thunkAPI.getState() as RootState;
    const config = state.dashboardConfig.config as DashboardConfig;
    const response = await apiClient.put<DashboardConfig>('/dashboard/config', config);
    thunkAPI.dispatch(fetchDashboardConfig());
    return normalizeDashboardConfig(response.data);
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to update dashboard config');
  }
});
