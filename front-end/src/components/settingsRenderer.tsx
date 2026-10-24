import React, { useState, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { SystemSettingValue } from "../stores/types/settings";
import type { LocalizableValue } from "../schemas/base";
import { LocalizableValueEditor } from "./localizableValueEditor";
import { NumberInput, TextInput, Select, Switch, Stack, Text, Group, ActionIcon, Box, Tooltip } from "@mantine/core";
import { DateInput } from "@mantine/dates";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

interface Setting {
  key: string;
  label: string;
  description: string;
  setting_type: "number" | "text" | "datetime" | "timestamp" | "boolean" | "select" | "localizable_text";
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
  onReset?: (key: string) => void;
  disabled?: boolean;
  showLabel?: boolean;
  resettable?: boolean;
}

const isLocalizableValue = (value: SystemSettingValue): value is LocalizableValue =>
  typeof value === "object" &&
  value !== null &&
  !(value instanceof Date) &&
  Object.values(value).every((translation) => typeof translation === "string");

const SettingsRenderer: React.FC<SettingsRendererProps> = ({
  setting,
  onChange,
  onReset,
  disabled = false,
  resettable = false,
}) => {
  const { t } = useTranslation();
  const [localValue, setLocalValue] = useState<SystemSettingValue>(setting.value ?? setting.default_value);
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

    if (onChange) {
      await onChange(setting.key, newValue);
    }
  };

  const handleReset = async () => {
    setError(null);
    setLocalValue(setting.default_value);

    if (onReset) {
      await onReset(setting.key);
    }
  };

  const renderNumberInput = () => {
    const value = typeof localValue === "number" ? localValue : 0;
    return (
      <NumberInput
        aria-label={setting.label}
        error={error}
        value={value}
        onChange={(val) => handleChange(val ?? 0)}
        min={setting.validation?.min}
        max={setting.validation?.max}
        disabled={disabled}
        step={1}
      />
    );
  };

  const renderTextInput = () => {
    const value = typeof localValue === "string" ? localValue : "";
    return (
      <TextInput
        aria-label={setting.label}
        error={error}
        value={value}
        onChange={(e) => handleChange(e.currentTarget.value)}
        disabled={disabled}
        pattern={setting.validation?.regex}
      />
    );
  };

  const renderLocalizableTextInput = () => {
    return (
      <LocalizableValueEditor
        t={t}
        label={setting.label}
        value={isLocalizableValue(localValue) ? localValue : {}}
        onChange={handleChange}
      />
    );
  };

  const renderDateTimeInput = () => {
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
        aria-label={setting.label}
        value={value}
        error={error}
        onChange={(val) => handleChange(val ? new Date(val).toISOString() : null)}
        disabled={disabled}
        withTime
        valueFormat="YYYY-MM-DDTHH:mm"
      />
    );
  };

  const renderTimestampInput = () => {
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
        aria-label={setting.label}
        value={value}
        error={error}
        onChange={(val) => handleChange(val ? new Date(val).getTime() : null)}
        disabled={disabled}
        withTime
        valueFormat="YYYY-MM-DDTHH:mm"
      />
    );
  };

  const renderBooleanInput = () => {
    const value = typeof localValue === "boolean" ? localValue : false;
    return (
      <Switch
        aria-label={setting.label}
        checked={value}
        error={error}
        onChange={(e) => handleChange(e.currentTarget.checked)}
        disabled={disabled}
        size="md"
      />
    );
  };

  const renderSelectInput = () => {
    const value = typeof localValue === "string" ? localValue : "";
    return (
      <Select
        aria-label={setting.label}
        value={value}
        error={error}
        onChange={(val) => handleChange(val ?? "")}
        disabled={disabled}
        data={setting.validation?.options?.map((option) => ({
          value: String(option.value),
          label: option.label,
        }))}
        clearable
      />
    );
  };

  const renderInput = () => {
    switch (setting.setting_type) {
      case "number":
        return renderNumberInput();
      case "text":
        return renderTextInput();
      case "localizable_text":
        return renderLocalizableTextInput();
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

  const isDefaultValue = useMemo(() => {
    const defaultValue = setting.default_value;
    if (
      setting.setting_type === "localizable_text" &&
      isLocalizableValue(localValue) &&
      isLocalizableValue(defaultValue)
    ) {
      const keys = Object.keys(localValue);
      return keys.length === Object.keys(defaultValue).length &&
        keys.every((key) => localValue[key] === defaultValue[key]);
    }
    return localValue === defaultValue;
  }, [localValue, setting.default_value, setting.setting_type]);

  return (
    <Stack gap="0">
      <Text size="sm" fw="bold">{setting.label}</Text>
      <Group wrap="nowrap" gap="xs">
        <Box style={{ flex: 1 }}>
          {renderInput()}
        </Box>
        {resettable && <Tooltip
            position="top"
            disabled={isDefaultValue}
            label={
              <Text fw={500} fz={13}>
                {t('settings.button.resetToDefault')}
              </Text>
          }>
            <ActionIcon
              variant="subtle"
              color="red"
              size="sm"
              style={{ flexShrink: 0 }}
              onClick={handleReset}
              disabled={isDefaultValue}
              aria-label={t("settings.resetToDefaults")}
            >
              <FontAwesomeIcon icon="rotate-left" size="xs" />
            </ActionIcon>
          </Tooltip>}
      </Group>
      <Text c='dimmed' size="xs">{setting.description}</Text>
    </Stack>
  );
};

export default SettingsRenderer;
