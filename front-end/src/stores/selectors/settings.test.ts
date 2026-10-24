import { createTestStore } from "../../test/storeTestUtils";
import {
  selectSettingByKey,
  selectSettings,
  selectSettingsByCategory,
  selectSettingsChanged,
  selectSettingsError,
  selectSettingsLoading,
} from "./settings";

const items = [
  { key: "discharge", label: { en: "Discharge", uk: "Розрядження" }, description: { en: "", uk: "" }, setting_type: "number" as const, default_value: 10, value: 10, category: { id: "power", label: { en: "Power", uk: "Потужність" } }, created_at: "", updated_at: "", changed: false, created: false },
  { key: "charge", label: { en: "Charge", uk: "Заряджання" }, description: { en: "", uk: "" }, setting_type: "number" as const, default_value: 97, value: 97, category: { id: "power", label: { en: "Power", uk: "Потужність" } }, created_at: "", updated_at: "", changed: true, created: false },
  { key: "email", label: { en: "Email", uk: "Електронна пошта" }, description: { en: "", uk: "" }, setting_type: "text" as const, default_value: "a@b.c", value: "a@b.c", category: { id: "notifications", label: { en: "Notifications", uk: "Сповіщення" } }, created_at: "", updated_at: "", changed: false, created: false },
];

const state = createTestStore({
  settings: { items, loading: false, creating: false, changed: true, error: null },
}).getState();

describe("settings selectors", () => {
  it("returns settings and their state flags", () => {
    expect(selectSettings(state)).toEqual(items);
    expect(selectSettingsLoading(state)).toBe(false);
    expect(selectSettingsError(state)).toBeNull();
    expect(selectSettingsChanged(state)).toBe(true);
  });

  it("groups settings by category", () => {
    expect(selectSettingsByCategory(state)).toEqual({
      power: { category: items[0].category, settings: items.slice(0, 2) },
      notifications: { category: items[2].category, settings: [items[2]] },
    });
  });

  it("finds a setting by key and returns undefined for an unknown key", () => {
    expect(selectSettingByKey(state, "charge")).toEqual(items[1]);
    expect(selectSettingByKey(state, "missing")).toBeUndefined();
  });
});
