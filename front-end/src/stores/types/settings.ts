export interface Setting {
  key: string;
  label: string;
  description: string;
  setting_type: "number" | "text" | "datetime" | "timestamp" | "boolean" | "select";
  default_value: any;
  value: any;
  validation?: {
    min?: number;
    max?: number;
    regex?: string;
    options?: Array<{ value: any; label: string }>;
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
  updates: Record<string, any>;
}

export interface SettingUpdateRequest {
  key: string;
  value: any;
}