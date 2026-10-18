export type SystemSettingValue = 
  | number 
  | string 
  | boolean 
  | Date 
  | null;

export interface Setting {
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
}

export interface SettingsState {
  items: Setting[];
  loading: boolean;
  error: string | null;
}

export interface SettingsGroupedByCategory {
  [category: string]: Setting[];
}

export interface BulkUpdateRequest {
  updates: Record<string, SystemSettingValue>;
}

export interface SettingUpdateRequest {
  key: string;
  value: SystemSettingValue;
}