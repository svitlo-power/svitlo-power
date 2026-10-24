import { ChangeEvent, FC, useCallback } from "react";
import { modals } from "@mantine/modals";
import { Button, Group, Stack, Switch } from "@mantine/core";
import { Controller, FieldErrors, useWatch } from "react-hook-form";
import { useFormHandler } from "../../../hooks";
import { useAppDispatch } from "../../../stores/store";
import {
  cancelEditingDashboardConfig,
  finishEditingDashboardConfig,
  startEditingDashboardConfig,
} from "../../../stores/slices";
import { dashboardEditSchema, DashboardEditType, toDashboardEditConfig } from "../../../schemas/dashboardEdit";
import { usePageTranslation } from "../../../utils";
import { LocalizableValue } from "../../../schemas";
import { AVAILABLE_LANGUAGES } from "../../../i18n";
import { LocalizableValueEditor } from "../../../components";
import { DashboardConfig } from "../../../stores/types";
import { OutagesScheduleSelection } from "./outagesScheduleSelection";

type OpenDashboardEditOptions = {
  dashboardConfig: DashboardConfig;
  title?: string;
};

export function openDashboardEditDialog({ dashboardConfig, title }: OpenDashboardEditOptions) {
  const formData = toDashboardEditConfig(dashboardConfig);

  const Inner: FC = () => {
    const dispatch = useAppDispatch();
    const t = usePageTranslation('dashboard');

    const getTitleError = (
      fieldErrors: FieldErrors<DashboardEditType>,
      culture: string,
    ): string | null => {
      const error = fieldErrors.title?.[culture];
      return error?.message ? t(error.message) : null;
    };

    const {
      handleFormSubmit,
      handleReset,
      renderField,
      control,
      isDirty,
      isValid,
      errors,
      setControlValue,
    } = useFormHandler<DashboardEditType>({
      validationSchema: dashboardEditSchema,
      fetchDataAction: () => {
        dispatch(startEditingDashboardConfig());
      },
      saveAction: (data) => {
        dispatch(finishEditingDashboardConfig({
          title: data.title,
          outagesSchedule: data.outagesSchedule.enable ? data.outagesSchedule : null,
        }));
      },
      cleanupAction: () => {
        dispatch(cancelEditingDashboardConfig());
      },
      formKey: "dashboard-edit-form",
      isEdit: true,
      initialData: formData,
      loading: false,
      useLocationGuard: false,
      errorFormatter: (error) => t(error),
      fields: [
        {
          name: "title",
          title: t('dashboardEdit.title'),
          render: (context) => <Controller
            name="title"
            control={context.helpers.control}
            defaultValue={{}}
            render={({ field }) => <LocalizableValueEditor
              t={t}
              label={context.title}
              value={field.value}
              onChange={(value: LocalizableValue) => context.helpers.setControlValue('title', value, true)}
              valueErrors={AVAILABLE_LANGUAGES.reduce(
                (previous, language) => ({
                  ...previous,
                  [language]: getTitleError(errors, language),
                }),
                {},
              )}
            />}
          />,
        },
      ],
    });

    const scheduleConfig = useWatch({ control, name: 'outagesSchedule' })
      ?? formData.outagesSchedule;
    const enabled = useWatch({ control, name: 'outagesSchedule.enable' })
      ?? formData.outagesSchedule.enable;
    const handleScheduleChange = useCallback((changes: Partial<DashboardEditType['outagesSchedule']>) => {
      if ('region' in changes) setControlValue('outagesSchedule.region', changes.region ?? null, true);
      if ('dso' in changes) setControlValue('outagesSchedule.dso', changes.dso ?? null, true);
      if ('queue' in changes) setControlValue('outagesSchedule.queue', changes.queue ?? null, true);
    }, [setControlValue]);

    const handleSave = () => {
      if (id) modals.close(id);
      handleFormSubmit();
    };

    const handleCancel = () => {
      if (id) modals.close(id);
      handleReset();
    };

    const hasCompleteSchedule = Boolean(
      scheduleConfig.region && scheduleConfig.dso && scheduleConfig.queue,
    );

    return (
      <Stack>
        {renderField('title')}
        <Controller
          name="outagesSchedule.enable"
          control={control}
          render={({ field }) => <Switch
            pb="xs"
            label={t('dashboardEdit.enableOutagesSchedule')}
            checked={field.value}
            onChange={(event: ChangeEvent<HTMLInputElement>) => {
              const value = event.currentTarget.checked;
              setControlValue('outagesSchedule.enable', value, true);
            }}
          />}
        />
        {enabled && <OutagesScheduleSelection
          value={scheduleConfig}
          t={t}
          onChange={handleScheduleChange}
        />}
        <Group justify="flex-end">
          <Button
            onClick={handleSave}
            disabled={!isDirty || !isValid || (enabled && !hasCompleteSchedule)}
          >
            {t('button.save')}
          </Button>
          <Button variant="default" onClick={handleCancel}>{t('button.cancel')}</Button>
        </Group>
      </Stack>
    );
  };

  const id: string | undefined = modals.open({
    title,
    centered: true,
    withCloseButton: false,
    closeOnClickOutside: false,
    closeOnEscape: false,
    children: <Inner />,
  });
}
