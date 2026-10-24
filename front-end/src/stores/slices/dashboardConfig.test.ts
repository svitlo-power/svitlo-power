import {
  cancelEditingDashboardConfig,
  dashboardConfigReducer,
  finishEditingDashboardConfig,
  startEditingDashboardConfig,
} from "./dashboardConfig";

const config = {
  title: { en: "Dashboard", uk: "Панель" },
  outagesSchedule: {
    enable: true,
    region: "Київ",
    dso: "ДТЕК",
    queue: "1.1",
  },
};

describe("dashboardConfig slice", () => {
  it("stores the edited nested configuration and marks it changed", () => {
    const state = dashboardConfigReducer(undefined, finishEditingDashboardConfig(config));

    expect(state.config).toEqual(config);
    expect(state.changed).toBe(true);
    expect(state.editingConfig).toBeUndefined();
  });

  it("keeps the current config while editing and clears the draft on cancel", () => {
    const initial = {
      config,
      loading: false,
      error: null,
      changed: false,
    };
    const editing = dashboardConfigReducer(initial, startEditingDashboardConfig());
    expect(editing.editingConfig).toEqual(config);

    const cancelled = dashboardConfigReducer(editing, cancelEditingDashboardConfig());
    expect(cancelled.config).toEqual(config);
    expect(cancelled.editingConfig).toBeUndefined();
    expect(cancelled.changed).toBe(false);
  });
});
