import { BaseEditableState } from "./base";
import type { LocalizableValue } from "../../schemas/base";

export type SystemSettingValue = 
  | number 
  | string 
  | boolean 
  | Date 
  | LocalizableValue
  | null;

export type SettingCategory = {
  id: string;
  label: LocalizableValue;
};

export type BaseServerSettingItem = {
  key: string;
  label: LocalizableValue;
  description: LocalizableValue;
  setting_type: "number" | "text" | "datetime" | "timestamp" | "boolean" | "select" | "localizable_text";
  default_value: SystemSettingValue;
  value: SystemSettingValue;
  editable: boolean;
  validation?: {
    min?: number;
    max?: number;
    regex?: string;
    options?: Array<{ value: SystemSettingValue; label: string }>;
  };
  category_id: string;
  created_at: string;
  updated_at: string;
};

export type ServerSettingItem = BaseServerSettingItem & {
  key: string;
};

export type Setting = Omit<ServerSettingItem, "category_id"> & {
  category: SettingCategory;
  changed: boolean;
  created: boolean;
};

export type FetchedSetting = Omit<ServerSettingItem, "category_id"> & {
  category: SettingCategory;
};

export type SettingsState = BaseEditableState & {
  items: Setting[];
  changed: boolean;
};

export type ServerSettingsGroupedResponse = {
  categories: Record<string, {
    id: string;
    label: LocalizableValue;
    settings: ServerSettingItem[];
  }>;
};

export type SettingsGroupedByCategory = Record<string, {
  category: SettingCategory;
  settings: Setting[];
}>;

export type BulkUpdateRequest = {
  updates: Record<string, SystemSettingValue>;
}

export type SettingUpdateRequest = {
  key: string;
  value: SystemSettingValue;
}