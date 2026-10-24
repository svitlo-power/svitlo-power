import { LocalizableValue } from "../../schemas";
import { BaseState } from "./base";
import { OutagesScheduleConfig } from "../../schemas/dashboardEdit";

export type DashboardConfig = {
  title: LocalizableValue;
  outagesSchedule: OutagesScheduleConfig | null;
};

export type DashboardConfigState = BaseState & {
  config?: DashboardConfig;
  editingConfig?: DashboardConfig;
  changed: boolean;
};