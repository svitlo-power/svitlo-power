import { createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";
import { RootState } from "../store";
import { ServerSettingItem, Setting } from "../types/settings";
import { settingSaved } from "../slices/settings";

export const fetchSettings = createAsyncThunk<ServerSettingItem[]>(
  "settings/fetchAll",
  async (_, thunkAPI) => {
    try {
      const response = await apiClient.get("/settings");
      const grouped = response.data.categories as Record<string, Setting[]>;
      const flattened: Setting[] = [];
      Object.values(grouped).forEach((settings) => {
        flattened.push(...settings);
      });
      return flattened;
    } catch (err: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(err) || "Failed to fetch settings");
    }
  }
);

export const saveSettings = createAsyncThunk(
  "settings/save",
  async (_, { getState, dispatch }) => {
    try {
      const state = getState() as RootState;
      const settingsState = state.settings;
      const promises = settingsState.items
        .filter((s: Setting) => s.changed)
        .map(async (setting: Setting) => {
          const serverDto = {
            key: setting.key,
            label: setting.label,
            description: setting.description,
            setting_type: setting.setting_type,
            default_value: setting.default_value,
            value: setting.value,
            validation: setting.validation,
            category: setting.category,
          };
          if (setting.created) {
            const response = await apiClient.post("/settings", serverDto);
            dispatch(settingSaved(response.data.key));
            return response.data;
          } else {
            const response = await apiClient.put(`/settings/${setting.key}`, serverDto);
            dispatch(settingSaved(response.data.key));
            return response.data;
          }
        });
      await Promise.all(promises);
      dispatch(fetchSettings());
    } catch (error: unknown) {
      console.error(error);
    }
  }
);

export const cancelSettingsEditing = createAsyncThunk(
  "settings/cancelEditing",
  async (_, { dispatch }) => {
    dispatch(fetchSettings());
  }
);