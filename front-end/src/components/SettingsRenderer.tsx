import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useDispatch } from "react-redux";
import { updateSetting } from "../stores/slices/settings";

interface Setting {
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
}

interface SettingsRendererProps {
  setting: Setting;
  onChange?: (key: string, value: any) => void;
  disabled?: boolean;
  showLabel?: boolean;
}

const SettingsRenderer: React.FC<SettingsRendererProps> = ({
  setting,
  onChange,
  disabled = false,
  showLabel = true,
}) => {
  const { t } = useTranslation();
  const dispatch = useDispatch();
  const [localValue, setLocalValue] = useState<any>(setting.value ?? setting.default_value);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update local value when setting.value changes
  useEffect(() => {
    setLocalValue(setting.value ?? setting.default_value);
  }, [setting.value, setting.default_value]);

  const validate = (value: any): string | null => {
    if (!setting.validation) return null;

    if (setting.setting_type === "number") {
      const num = Number(value);
      if (isNaN(num)) return t("settings.validation.notANumber");
      if (setting.validation.min !== undefined && num < setting.validation.min) {
        return t("settings.validation.min", { min: setting.validation.min });
      }
      if (setting.validation.max !== undefined && num > setting.validation.max) {
        return t("settings.validation.max", { max: setting.validation.max });
      }
    }

    if (setting.setting_type === "text" && setting.validation.regex) {
      const regex = new RegExp(setting.validation.regex);
      if (!regex.test(value)) {
        return t("settings.validation.patternMismatch");
      }
    }

    if (setting.setting_type === "select" && setting.validation.options) {
      const validValues = setting.validation.options.map((o) => o.value);
      if (!validValues.includes(value)) {
        return t("settings.validation.invalidOption");
      }
    }

    return null;
  };

  const handleChange = async (newValue: any) => {
    setError(null);
    const validationError = validate(newValue);
    if (validationError) {
      setError(validationError);
      return;
    }

    setLocalValue(newValue);
    setIsSaving(true);

    try {
      if (onChange) {
        await onChange(setting.key, newValue);
      } else {
        await dispatch(updateSetting({ key: setting.key, value: newValue })).unwrap();
      }
    } catch (err) {
      setError(t("settings.error.saveFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const renderNumberInput = () => (
    <input
      type="number"
      className="form-control"
      value={localValue}
      onChange={(e) => handleChange(Number(e.target.value) || 0)}
      min={setting.validation?.min}
      max={setting.validation?.max}
      disabled={disabled || isSaving}
      step="any"
    />
  );

  const renderTextInput = () => (
    <input
      type="text"
      className="form-control"
      value={localValue}
      onChange={(e) => handleChange(e.target.value)}
      disabled={disabled || isSaving}
      pattern={setting.validation?.regex}
    />
  );

  const renderDateTimeInput = () => (
    <input
      type="datetime-local"
      className="form-control"
      value={localValue ? new Date(localValue).toISOString().slice(0, 16) : ""}
      onChange={(e) => handleChange(e.target.value ? new Date(e.target.value).toISOString() : null)}
      disabled={disabled || isSaving}
    />
  );

  const renderTimestampInput = () => (
    <input
      type="datetime-local"
      className="form-control"
      value={localValue ? new Date(localValue).toISOString().slice(0, 16) : ""}
      onChange={(e) => handleChange(e.target.value ? new Date(e.target.value).getTime() : null)}
      disabled={disabled || isSaving}
    />
  );

  const renderBooleanInput = () => (
    <div className="form-check form-switch">
      <input
        type="checkbox"
        className="form-check-input"
        checked={Boolean(localValue)}
        onChange={(e) => handleChange(e.target.checked)}
        disabled={disabled || isSaving}
        role="switch"
      />
    </div>
  );

  const renderSelectInput = () => (
    <select
      className="form-select"
      value={localValue}
      onChange={(e) => handleChange(e.target.value)}
      disabled={disabled || isSaving}
    >
      {setting.validation?.options?.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );

  const renderInput = () => {
    switch (setting.setting_type) {
      case "number":
        return renderNumberInput();
      case "text":
        return renderTextInput();
      case "datetime":
        return renderDateTimeInput();
      case "timestamp":
        return renderTimestampInput();
      case "boolean":
        return renderBooleanInput();
      case "select":
        return renderSelectInput();
      default:
        return <span className="text-muted">{t("settings.unknownType")}</span>;
    }
  };

  return (
    <div className="mb-3">
      {showLabel && (
        <label className="form-label fw-medium">
          {setting.label}
          {isSaving && <FontAwesomeIcon icon="spinner" className="ms-2 fa-spin" />}
        </label>
      )}
      <div className="input-group">
        {renderInput()}
        {setting.setting_type === "boolean" && showLabel && (
          <span className="input-group-text bg-transparent border-0 px-0">
            {setting.label}
          </span>
        )}
      </div>
      {setting.description && (
        <div className="form-text">{setting.description}</div>
      )}
      {error && (
        <div className="text-danger small mt-1">{error}</div>
      )}
    </div>
  );
};

export default SettingsRenderer;