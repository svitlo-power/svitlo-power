import { settingsReducer, resetSetting } from "./settings";

const setting = {
  key: "discharge",
  label: { en: "Discharge target", uk: "Ціль розрядження" },
  description: { en: "Battery target", uk: "Ціль батареї" },
  setting_type: "number" as const,
  default_value: 10,
  value: 20,
  editable: true,
  category: {
    id: "power_estimation",
    label: { en: "Power Estimation", uk: "Оцінка потужності" },
  },
  changed: false,
  created: false,
};

describe("settings slice", () => {
  it("resets a setting to its default and marks it as changed", () => {
    const state = settingsReducer(
      { items: [setting], loading: false, creating: false, changed: false, error: null },
      resetSetting(setting.key),
    );

    expect(state.items[0]).toMatchObject({ value: 10, changed: true });
    expect(state.changed).toBe(true);
  });

  it("leaves state unchanged when resetting an unknown setting", () => {
    const state = settingsReducer(
      { items: [setting], loading: false, creating: false, changed: false, error: null },
      resetSetting("unknown"),
    );

    expect(state).toMatchObject({ items: [setting], changed: false });
  });
});
