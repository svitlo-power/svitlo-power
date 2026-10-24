import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import {
  FetchedSetting,
  SettingsState,
  Setting,
  SystemSettingValue,
} from "../types/settings";
import { fetchSettings, saveSettings, cancelSettingsEditing } from "../thunks/settings";

const initialState: SettingsState = {
  items: [],
  loading: false,
  creating: false,
  changed: false,
  error: null,
};

export type UpdateSettingActionPayload = {
  key: string;
  value: Setting;
};

export const settingsSlice = createSlice({
  name: "settings",
  initialState,
  reducers: {
    updateSetting(state, { payload }: PayloadAction<{ key: string; value: SystemSettingValue }>) {
      const setting = state.items.find(s => s.key === payload.key);
      if (setting) {
        setting.value = payload.value;
        setting.changed = true;
        state.changed = true;
      }
    },
    settingSaved(state, { payload }: PayloadAction<string>) {
      const setting = state.items.find(s => s.key === payload);
      if (setting) {
        setting.changed = false;
      }
    },
    resetSetting(state, { payload }: PayloadAction<string>) {
      const setting = state.items.find(s => s.key === payload);
      if (setting) {
        const changed = setting.value !== setting.default_value;
        setting.value = setting.default_value;
        setting.changed = state.changed || changed;
        state.changed = state.items.some(s => s.changed);
      }
    },
    startEditingSetting(state) {
      state.creating = true;
    },
    cancelEditingSetting(state) {
      state.creating = false;
    },
    createSetting(state, { payload }: PayloadAction<Setting>) {
      state.creating = false;
      state.items.push({
        key: payload.key,
        label: payload.label,
        description: payload.description,
        setting_type: payload.setting_type,
        default_value: payload.default_value,
        value: payload.default_value,
        validation: payload.validation,
        category: payload.category,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        changed: true,
        created: true,
      });
    },
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
      .addCase(fetchSettings.fulfilled, (state, action: PayloadAction<FetchedSetting[]>) => {
        state.items = action.payload.map(item => ({ ...item, changed: false, created: false }));
        state.loading = false;
        state.creating = false;
        state.changed = false;
      })
      .addCase(fetchSettings.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
    builder
      .addCase(saveSettings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(saveSettings.fulfilled, (state) => {
        state.loading = false;
        state.creating = false;
      })
      .addCase(saveSettings.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
    builder
      .addCase(cancelSettingsEditing.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(cancelSettingsEditing.fulfilled, (state) => {
        state.loading = false;
        state.creating = false;
      })
      .addCase(cancelSettingsEditing.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { updateSetting, settingSaved, resetSetting, startEditingSetting, cancelEditingSetting, createSetting, clearError } = settingsSlice.actions;
export const settingsReducer = settingsSlice.reducer;