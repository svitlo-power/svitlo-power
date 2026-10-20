import React, { useCallback, useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch, useSelector } from "react-redux";
import { AppDispatch } from "../../stores/store";
import {
  fetchSettings,
  saveSettings,
  cancelSettingsEditing,
} from "../../stores/thunks/settings";
import {
  selectSettingsByCategory,
  selectSettingsLoading,
  selectSettingsError,
  selectSettingsChanged,
} from "../../stores/selectors/settings";
import { updateSetting } from "../../stores/slices/settings";
import { Page } from "../../components/page";
import { SystemSettingValue } from "../../stores/types/settings";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { useLocalizedEffect } from "../../hooks";
import { ErrorMessage } from "../../components";
import { CategorySection } from "./components/categorySection";
import { Accordion } from "@mantine/core";

export const SystemSettingsPage: React.FC = () => {
  const { t } = useTranslation();
  const dispatch = useDispatch<AppDispatch>();
  const settingsByCategory = useSelector(selectSettingsByCategory);
  const loading = useSelector(selectSettingsLoading);
  const changed = useSelector(selectSettingsChanged);
  const error = useSelector(selectSettingsError);

  useEffect(() => {
    dispatch(fetchSettings());
  }, [dispatch]);

  const handleUpdate = (key: string, value: SystemSettingValue) => {
    dispatch(updateSetting({ key, value }));
  };

  const handleSave = useCallback(async () => {
    await dispatch(saveSettings()).unwrap();
  }, [dispatch]);

  const handleReset = useCallback(async () => {
    try {
        await dispatch(cancelSettingsEditing()).unwrap();
    } catch (err) {
        console.error("Failed to reset settings:", err);
    }
  }, [dispatch]);

  const getHeaderButtons = useCallback((dataChanged: boolean): PageHeaderButton[] => [
    { text: t('button.save'), icon: "save", color: "green", onClick: handleSave, disabled: !dataChanged, },
    { text: t('button.cancel'), icon: "cancel", color: "black", onClick: handleReset, disabled: !dataChanged, },
  ], [t, handleSave, handleReset]);
  const { setHeaderButtons } = useHeaderContent();
  useLocalizedEffect(() => {
    setHeaderButtons(getHeaderButtons(changed));
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons, changed]);

  const defExpanded = useMemo(() => {
    const keys = Object.keys(settingsByCategory);
    return keys.length > 0 ? keys[0] : null;
  }, [settingsByCategory]);

  return (
    <Page loading={loading} p={'md'}>
      { error && <ErrorMessage content={error} />}
      {Object.keys(settingsByCategory).length === 0
        ? (
          <div className="text-center py-5">
            <p className="text-muted">{t("settings.noSettings")}</p>
          </div>
        ) : (
          <Accordion defaultValue={defExpanded} variant="contained">
            {Object.entries(settingsByCategory).map(([category, settings], idx) => (
              <CategorySection
                key={category}
                category={category}
                settings={settings}
                onUpdate={handleUpdate}
              />
            ))}
          </Accordion>
        )}
    </Page>
  );
};
