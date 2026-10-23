import { SettingsState, SettingsGroupedByCategory } from "../types/settings";
import { RootState } from "../store";

export const selectSettings = (state: RootState): SettingsState["items"] => state.settings.items;
export const selectSettingsLoading = (state: RootState): boolean => state.settings.loading;
export const selectSettingsError = (state: RootState): string | null => state.settings.error;

export const selectSettingsByCategory = (state: RootState): SettingsGroupedByCategory => {
  const grouped: SettingsGroupedByCategory = {};
  state.settings.items.forEach((setting) => {
    if (!grouped[setting.category]) {
      grouped[setting.category] = [];
    }
    grouped[setting.category].push(setting);
  });
  return grouped;
};

export const selectSettingByKey = (state: RootState, key: string) =>
  state.settings.items.find((s) => s.key === key);

export const selectSettingsChanged = (state: RootState): boolean =>
  state.settings.changed;