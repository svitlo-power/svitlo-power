import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useAppDispatch } from "../stores/store";
import { updateSetting } from "../stores/slices/settings";
import { SystemSettingValue } from "../stores/types/settings";
import { NumberInput, TextInput, Select, Switch, Stack } from "@mantine/core";
import { DateInput } from "@mantine/dates";

interface Setting {
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
}

interface SettingsRendererProps {
  setting: Setting;
  onChange?: (key: string, value: SystemSettingValue) => void;
  disabled?: boolean;
  showLabel?: boolean;
}

type InputRendererFnProps = {
  title: string;
  description: string;
  error: string | null;
};
type InputRendererFn = (props: InputRendererFnProps) => React.ReactElement;

const SettingsRenderer: React.FC<SettingsRendererProps> = ({
  setting,
  onChange,
  disabled = false,
}) => {
  const { t } = useTranslation();
  const dispatch = useAppDispatch();
  const [localValue, setLocalValue] = useState<SystemSettingValue>(setting.value ?? setting.default_value);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Update local value when setting.value changes
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLocalValue(setting.value ?? setting.default_value);
  }, [setting.value, setting.default_value]);

  const validate = (value: SystemSettingValue): string | null => {
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
      if (value && !regex.test(value as string)) {
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

  const handleChange = async (newValue: SystemSettingValue) => {
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
        // @ts-expect-error - dispatch thunk action
        await (dispatch as AppDispatch)(updateSetting({ key: setting.key, value: newValue })).unwrap();
      }
    } catch {
      setError(t("settings.error.saveFailed"));
    } finally {
      setIsSaving(false);
    }
  };

  const renderNumberInput:InputRendererFn = (props) => {
    const value = typeof localValue === "number" ? localValue : 0;
    return (
      <NumberInput
        label={props.title}
        description={props.description}
        error={props.error}
        value={value}
        onChange={(val) => handleChange(val ?? 0)}
        min={setting.validation?.min}
        max={setting.validation?.max}
        disabled={disabled || isSaving}
        step={1}
      />
    );
  };

  const renderTextInput:InputRendererFn = (props) => {
    const value = typeof localValue === "string" ? localValue : "";
    return (
      <TextInput
        label={props.title}
        description={props.description}
        error={props.error}
        value={value}
        onChange={(e) => handleChange(e.currentTarget.value)}
        disabled={disabled || isSaving}
        pattern={setting.validation?.regex}
      />
    );
  };

  const renderDateTimeInput:InputRendererFn = (props) => {
    let value: Date | null = null;
    if (localValue instanceof Date) {
      value = localValue;
    } else if (typeof localValue === "string" && localValue) {
      value = new Date(localValue);
    } else if (typeof localValue === "number" && localValue) {
      value = new Date(localValue);
    }
    return (
      <DateInput
        label={props.title}
        description={props.description}
        value={value}
        error={props.error}
        onChange={(val) => handleChange(val ? new Date(val).toISOString() : null)}
        disabled={disabled || isSaving}
        withTime
        valueFormat="YYYY-MM-DDTHH:mm"
      />
    );
  };

  const renderTimestampInput:InputRendererFn = (props) => {
    let value: Date | null = null;
    if (localValue instanceof Date) {
      value = localValue;
    } else if (typeof localValue === "string" && localValue) {
      value = new Date(localValue);
    } else if (typeof localValue === "number" && localValue) {
      value = new Date(localValue);
    }
    return (
      <DateInput
        label={props.title}
        description={props.description}
        value={value}
        error={props.error}
        onChange={(val) => handleChange(val ? new Date(val).getTime() : null)}
        disabled={disabled || isSaving}
        withTime
        valueFormat="YYYY-MM-DDTHH:mm"
      />
    );
  };

  const renderBooleanInput:InputRendererFn = (props) => {
    const value = typeof localValue === "boolean" ? localValue : false;
    return (
      <Switch
        label={props.title}
        description={props.description}
        checked={value}
        error={props.error}
        onChange={(e) => handleChange(e.currentTarget.checked)}
        disabled={disabled || isSaving}
        size="md"
      />
    );
  };

  const renderSelectInput:InputRendererFn = (props) => {
    const value = typeof localValue === "string" ? localValue : "";
    return (
      <Select
        label={props.title}
        description={props.description}
        value={value}
        error={props.error}
        onChange={(val) => handleChange(val ?? "")}
        disabled={disabled || isSaving}
        data={setting.validation?.options?.map((option) => ({
          value: String(option.value),
          label: option.label,
        }))}
        clearable
      />
    );
  };

  const renderInput = () => {
    const renderArgs = {
      title: setting.label,
      description: setting.description,
      error: error,
    };
    switch (setting.setting_type) {
      case "number":
        return renderNumberInput(renderArgs);
      case "text":
        return renderTextInput(renderArgs);
      case "datetime":
        return renderDateTimeInput(renderArgs);
      case "timestamp":
        return renderTimestampInput(renderArgs);
      case "boolean":
        return renderBooleanInput(renderArgs);
      case "select":
        return renderSelectInput(renderArgs);
      default:
        return <span className="text-muted">{t("settings.unknownType")}</span>;
    }
  };

  return (
    <Stack gap="md">
      {renderInput()}
    </Stack>
  );
};

export default SettingsRenderer;