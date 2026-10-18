import React, { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDispatch, useSelector } from "react-redux";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faSave,
  faUndo,
  faSpinner,
  faChevronDown,
  faChevronUp,
} from "@fortawesome/free-solid-svg-icons";
import { RootState, AppDispatch } from "../stores/store";
import {
  fetchSettings,
  updateSetting,
  bulkUpdateSettings,
  resetSettings,
  selectSettingsByCategory,
  selectSettingsLoading,
  selectSettingsError,
} from "../stores/settingsSlice";
import SettingsRenderer from "../components/SettingsRenderer";
import { Page } from "../components/page";

interface CategorySectionProps {
  category: string;
  settings: any[];
  onUpdate: (key: string, value: any) => void;
  expanded: boolean;
  onToggle: () => void;
}

const CategorySection: React.FC<CategorySectionProps> = ({
  category,
  settings,
  onUpdate,
  expanded,
  onToggle,
}) => {
  const { t } = useTranslation();

  const categoryLabel = t(`settings.categories.${category}`) || category;

  return (
    <div className="card mb-3">
      <div
        className="card-header bg-light"
        onClick={onToggle}
        style={{ cursor: "pointer" }}
      >
        <h5 className="mb-0 d-flex justify-content-between align-items-center">
          <span>{categoryLabel}</span>
          <FontAwesomeIcon
            icon={expanded ? faChevronUp : faChevronDown}
            className="text-muted"
          />
        </h5>
      </div>
      {expanded && (
        <div className="card-body">
          {settings.map((setting) => (
            <SettingsRenderer
              key={setting.key}
              setting={setting}
              onChange={onUpdate}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const SystemSettings: React.FC = () => {
  const { t } = useTranslation();
  const dispatch = useDispatch<AppDispatch>();
  const settingsByCategory = useSelector(selectSettingsByCategory);
  const loading = useSelector(selectSettingsLoading);
  const error = useSelector(selectSettingsError);
  const [expandedCategories, setExpandedCategories] = useState<Record<string, boolean>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [pendingChanges, setPendingChanges] = useState<Record<string, any>>({});

  useEffect(() => {
    dispatch(fetchSettings());
  }, [dispatch]);

  useEffect(() => {
    // Initialize expanded state for all categories
    const initialExpanded: Record<string, boolean> = {};
    Object.keys(settingsByCategory).forEach((cat) => {
      initialExpanded[cat] = true;
    });
    setExpandedCategories(initialExpanded);
  }, [settingsByCategory]);

  const handleUpdate = (key: string, value: any) => {
    setPendingChanges((prev) => ({ ...prev, [key]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    if (Object.keys(pendingChanges).length === 0) return;

    try {
      await dispatch(bulkUpdateSettings({ updates: pendingChanges })).unwrap();
      setPendingChanges({});
      setHasChanges(false);
    } catch (err) {
      console.error("Failed to save settings:", err);
    }
  };

  const handleReset = async () => {
    if (!window.confirm(t("settings.confirmReset"))) return;

    try {
      await dispatch(resetSettings()).unwrap();
      setPendingChanges({});
      setHasChanges(false);
    } catch (err) {
      console.error("Failed to reset settings:", err);
    }
  };

  const toggleCategory = (category: string) => {
    setExpandedCategories((prev) => ({
      ...prev,
      [category]: !prev[category],
    }));
  };

  if (loading) {
    return (
      <Page title={t("settings.title")}>
        <div className="text-center py-5">
          <FontAwesomeIcon icon={faSpinner} className="fa-spin fa-2x" />
          <p className="mt-2">{t("settings.loading")}</p>
        </div>
      </Page>
    );
  }

  if (error) {
    return (
      <Page title={t("settings.title")}>
        <div className="alert alert-danger">{error}</div>
      </Page>
    );
  }

  return (
    <Page title={t("settings.title")}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>{t("settings.title")}</h1>
        <div className="btn-group">
          <button
            className="btn btn-outline-secondary"
            onClick={handleReset}
            disabled={loading}
          >
            <FontAwesomeIcon icon={faUndo} className="me-1" />
            {t("settings.resetToDefaults")}
          </button>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={!hasChanges || loading}
          >
            <FontAwesomeIcon icon={faSave} className="me-1" />
            {t("settings.saveChanges")}
          </button>
        </div>
      </div>

      {hasChanges && (
        <div className="alert alert-warning alert-dismissible fade show mb-4" role="alert">
          {t("settings.unsavedChanges")}
          <button
            type="button"
            className="btn-close"
            onClick={() => {
              setPendingChanges({});
              setHasChanges(false);
            }}
            aria-label="Close"
          />
        </div>
      )}

      {Object.keys(settingsByCategory).length === 0 ? (
        <div className="text-center py-5">
          <p className="text-muted">{t("settings.noSettings")}</p>
        </div>
      ) : (
        Object.entries(settingsByCategory).map(([category, settings]) => (
          <CategorySection
            key={category}
            category={category}
            settings={settings}
            onUpdate={handleUpdate}
            expanded={expandedCategories[category] ?? true}
            onToggle={() => toggleCategory(category)}
          />
        ))
      )}
    </Page>
  );
};

export default SystemSettings;