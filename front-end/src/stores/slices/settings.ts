import { createSlice, createAsyncThunk, PayloadAction } from "@reduxjs/toolkit";
import { SettingsState, Setting, SettingsGroupedByCategory, BulkUpdateRequest } from "../types/settings";
import apiClient from "../../utils/apiClient";

const initialState: SettingsState = {
  items: [],
  loading: false,
  error: null,
};

export const fetchSettings = createAsyncThunk<Setting[]>(
  "settings/fetchAll",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.get("/settings");
      // Flatten the grouped settings
      const grouped = response.data.categories as SettingsGroupedByCategory;
      const flattened: Setting[] = [];
      Object.values(grouped).forEach((settings) => {
        flattened.push(...settings);
      });
      return flattened;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || "Failed to fetch settings");
    }
  }
);

export const updateSetting = createAsyncThunk<Setting, { key: string; value: any }>(
  "settings/update",
  async ({ key, value }, { rejectWithValue }) => {
    try {
      const response = await apiClient.put(`/settings/${key}`, { value });
      return response.data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || "Failed to update setting");
    }
  }
);

export const bulkUpdateSettings = createAsyncThunk<Record<string, boolean>, BulkUpdateRequest>(
  "settings/bulkUpdate",
  async ({ updates }, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/settings/bulk", { updates });
      return response.data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || "Failed to bulk update settings");
    }
  }
);

export const resetSettings = createAsyncThunk<{ reset_count: number }>(
  "settings/reset",
  async (_, { rejectWithValue }) => {
    try {
      const response = await apiClient.post("/settings/reset");
      return response.data;
    } catch (err: any) {
      return rejectWithValue(err.response?.data?.detail || "Failed to reset settings");
    }
  }
);

export const settingsSlice = createSlice({
  name: "settings",
  initialState,
  reducers: {
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchSettings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSettings.fulfilled, (state, action: PayloadAction<Setting[]>) => {
        state.items = action.payload;
        state.loading = false;
      })
      .addCase(fetchSettings.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(updateSetting.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(updateSetting.fulfilled, (state, action: PayloadAction<Setting>) => {
        const index = state.items.findIndex((s) => s.key === action.payload.key);
        if (index >= 0) {
          state.items[index] = action.payload;
        }
        state.loading = false;
      })
      .addCase(updateSetting.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(bulkUpdateSettings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(bulkUpdateSettings.fulfilled, (state) => {
        // Refresh settings after bulk update
        state.loading = false;
      })
      .addCase(bulkUpdateSettings.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });

    builder
      .addCase(resetSettings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(resetSettings.fulfilled, (state) => {
        // Reset values to defaults
        state.items = state.items.map((s) => ({ ...s, value: s.default_value }));
        state.loading = false;
      })
      .addCase(resetSettings.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearError } = settingsSlice.actions;
export const settingsReducer = settingsSlice.reducer;

// Selectors
export const selectSettings = (state: { settings: SettingsState }) => state.settings.items;
export const selectSettingsLoading = (state: { settings: SettingsState }) => state.settings.loading;
export const selectSettingsError = (state: { settings: SettingsState }) => state.settings.error;

export const selectSettingsByCategory = (state: { settings: SettingsState }): SettingsGroupedByCategory => {
  const grouped: SettingsGroupedByCategory = {};
  state.settings.items.forEach((setting) => {
    if (!grouped[setting.category]) {
      grouped[setting.category] = [];
    }
    grouped[setting.category].push(setting);
  });
  return grouped;
};

export const selectSettingByKey = (state: { settings: SettingsState }, key: string) =>
  state.settings.items.find((s) => s.key === key);