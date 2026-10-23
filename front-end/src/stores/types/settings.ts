import { BaseEditableState } from "./base";

export type SystemSettingValue = 
  | number 
  | string 
  | boolean 
  | Date 
  | null;

export type BaseServerSettingItem = {
  key: string;
  label: string;
  description: string;
  setting_type: "number" | "text" | "datetime" | "timestamp" | "boolean" | "select";
  default_value: SystemSettingValue;
  value: SystemSettingValue;
  validation?: {
    min?: number;
    max?: number;
    regex?: string;
    options?: Array<{ value: SystemSettingValue; label: string }>;
  };
  category: string;
  created_at: string;
  updated_at: string;
};

export type ServerSettingItem = BaseServerSettingItem & {
  key: string;
};

export type Setting = ServerSettingItem & {
  changed: boolean;
  created: boolean;
};

export type SettingsState = BaseEditableState & {
  items: Setting[];
  changed: boolean;
};

export type SettingsGroupedByCategory = {
  [category: string]: Setting[];
}

export type BulkUpdateRequest = {
  updates: Record<string, SystemSettingValue>;
}

export type SettingUpdateRequest = {
  key: string;
  value: SystemSettingValue;
}