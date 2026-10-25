import { FC, useMemo } from "react";
import { modals } from "@mantine/modals";
import {
  Button,
  Checkbox,
  ColorInput,
  Group,
  Loader,
  MultiSelect,
  parseThemeColor,
  Select,
  Stack,
  TextInput,
  useMantineColorScheme,
  useMantineTheme,
} from "@mantine/core";
import { useFormHandler, useLookup } from "../../../hooks";
import { useAppDispatch, useAppSelector } from "../../../stores/store";
import {
  buildingEditSchema,
  BuildingEditType,
  LocalizableValue,
  ObjectId,
} from "../../../schemas";
import { startEditingBuilding } from "../../../stores/thunks";
import {
  cancelEditingOrCreatingBuilding,
  finishCreatingBuilding,
  finishEditingBuilding,
  startCreatingBuilding,
} from "../../../stores/slices";
import { Controller, FieldErrors } from "react-hook-form";
import { LookupSchema } from "../../../types";
import { usePageTranslation } from "../../../utils";
import { LocalizableValueEditor } from "../../../components";
import { AVAILABLE_LANGUAGES } from "../../../i18n";

type OpenBuildingEditOptions = {
  creating?: boolean;
  buildingId?: ObjectId;
  title?: string;
};

export function openBuildingEditDialog({
  creating = false,
  buildingId,
  title,
}: OpenBuildingEditOptions) {
  const Inner: FC = () => {
    const building = useAppSelector((state) => state.buildings.editingItem!);
    const loading = useAppSelector((state) => state.buildings.loading);
    const dispatch = useAppDispatch();
    const t = usePageTranslation("dashboard");

    const theme = useMantineTheme();
    const { colorScheme } = useMantineColorScheme();

    const { data: stations, loading: stationsLoading } = useLookup(
      LookupSchema.Station,
    );
    const { data: users, loading: usersLoading } = useLookup(
      LookupSchema.ReporterUser,
    );

    const stationOptions = useMemo(
      () =>
        stationsLoading
          ? []
          : stations.map((station) => ({
              label: station.text,
              value: station.value!,
            })),
      [stations, stationsLoading],
    );
    const userOptions = useMemo(
      () =>
        usersLoading
          ? []
          : users.map((user) => ({
              label: user.text,
              value: user.value!,
            })),
      [users, usersLoading],
    );

    const getNameError = (
      fieldErrors: FieldErrors<BuildingEditType>,
      culture: string,
    ): string | null => {
      const error = fieldErrors.name?.[culture];
      return error?.message ? t(error.message!) : null;
    };

    const {
      handleFormSubmit,
      handleReset,
      renderField,
      isDirty,
      isValid,
      errors,
    } = useFormHandler<BuildingEditType>({
      validationSchema: buildingEditSchema,
      fetchDataAction: () => {
        if (!creating) {
          dispatch(startEditingBuilding(buildingId!));
        } else {
          dispatch(startCreatingBuilding());
        }
      },
      saveAction: (data: BuildingEditType) => {
        if (creating) {
          dispatch(finishCreatingBuilding(data));
        } else {
          dispatch(finishEditingBuilding(data));
        }
      },
      cleanupAction: () => {
        dispatch(cancelEditingOrCreatingBuilding());
      },
      formKey: "dashboard-edit-form",
      isEdit: true,
      initialData: building,
      loading: loading || usersLoading || stationsLoading,
      useLocationGuard: false,
      defaultRender: (name, title, context) => {
        return (
          <TextInput
            required
            label={title}
            {...context.helpers.registerControl(name)}
          />
        );
      },
      errorFormatter: (error) => t(error),
      fields: [
        {
          name: "name",
          title: t("buildingEdit.name"),
          render: (context) => {
            return (
              <Controller
                name="name"
                control={context.helpers.control}
                defaultValue={{}}
                render={({ field }) => (
                  <>
                    <LocalizableValueEditor
                      t={t}
                      label={context.title}
                      value={field.value}
                      onChange={(value: LocalizableValue) =>
                        context.helpers.setControlValue("name", value, true)
                      }
                      valueErrors={AVAILABLE_LANGUAGES.reduce(
                        (prev, curr) => ({
                          ...prev,
                          [curr]: getNameError(errors, curr),
                        }),
                        {},
                      )}
                    />
                  </>
                )}
              />
            );
          },
        },
        {
          name: "enabled",
          title: t("buildingEdit.enabled"),
          render: (context) => {
            return (
              <Controller
                name="enabled"
                control={context.helpers.control}
                render={({ field }) => (
                  <Checkbox
                    pb="xs"
                    label={context.title}
                    checked={field.value || false}
                    onChange={(x) => {
                      context.helpers.setControlValue(
                        "enabled",
                        x.currentTarget.checked,
                        true,
                      );
                    }}
                  />
                )}
              />
            );
          },
        },
        {
          name: "color",
          title: t("buildingEdit.color"),
          render: (context) => {
            const selectedColor = context.helpers.getControlValue("color");
            let color: string | undefined = undefined;
            if (selectedColor) {
              color = parseThemeColor({
                color: context.helpers.getControlValue("color"),
                theme,
                colorScheme,
              }).value;
            }
            return (
              <ColorInput
                label={context.title}
                rightSection={loading ? "Loading..." : null}
                swatches={[...Object.values(theme.colors).flat()]}
                swatchesPerRow={15}
                {...context.helpers.registerControl("color")}
                value={color}
                onChange={(value) =>
                  context.helpers.setControlValue("color", value, true)
                }
              />
            );
          },
        },
        {
          name: "stationId",
          title: t("buildingEdit.station"),
          render: (context) => {
            return (
              <Controller
                name="stationId"
                control={context.helpers.control}
                defaultValue={"0"}
                render={({ field }) => (
                  <Select
                    clearable
                    data={stationOptions}
                    {...field}
                    leftSection={stationsLoading ? <Loader size="xs" /> : null}
                    label={context.title}
                    value={field.value ?? ""}
                    error={context.helpers.getFieldError("stationId")}
                    onChange={(value) =>
                      context.helpers.setControlValue("stationId", value, true)
                    }
                  />
                )}
              />
            );
          },
        },
        {
          name: "reportUserIds",
          title: t("buildingEdit.reportUsers"),
          render: (context) => {
            return (
              <Controller
                name="reportUserIds"
                control={context.helpers.control}
                defaultValue={[]}
                render={({ field }) => (
                  <MultiSelect
                    required
                    data={userOptions}
                    {...field}
                    leftSection={usersLoading ? <Loader size="xs" /> : null}
                    label={context.title}
                    value={field.value ?? []}
                    error={context.helpers.getFieldError("reportUserIds")}
                    onChange={(value) =>
                      context.helpers.setControlValue(
                        "reportUserIds",
                        value,
                        true,
                        false,
                      )
                    }
                  />
                )}
              />
            );
          },
        },
      ],
    });

    const handleSave = () => {
      if (id) {
        modals.close(id);
      }
      handleFormSubmit();
    };

    const handleCancel = () => {
      if (id) {
        modals.close(id);
      }
      handleReset();
    };

    return (
      <Stack>
        {renderField("name")}
        {renderField("enabled")}
        {renderField("color")}
        {renderField("stationId")}
        {renderField("reportUserIds")}
        <Group justify="flex-end">
          <Button onClick={handleSave} disabled={!isDirty || !isValid}>
            {t("button.save")}
          </Button>
          <Button variant="default" onClick={handleCancel}>
            {t("button.cancel")}
          </Button>
        </Group>
      </Stack>
    );
  };

  const id: string | undefined = modals.open({
    title: title,
    size: "lg",
    centered: true,
    withCloseButton: false,
    closeOnClickOutside: false,
    closeOnEscape: false,
    children: <Inner />,
  });
}
