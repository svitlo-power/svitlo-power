import { settingsReducer, updateSetting } from "./settings";

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
  it("updates a setting and marks it as changed", () => {
    const state = settingsReducer(
      { items: [setting], loading: false, creating: false, changed: false, error: null },
      updateSetting({ key: setting.key, value: 30 }),
    );

    expect(state.items[0]).toMatchObject({ value: 30, changed: true });
    expect(state.changed).toBe(true);
  });
});
