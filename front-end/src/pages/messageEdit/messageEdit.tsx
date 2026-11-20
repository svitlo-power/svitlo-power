import {
  ChangeEvent,
  FC,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useHeaderContent } from "../../providers";
import { useAppDispatch, useAppSelector } from "../../stores/store";
import {
  editMessage,
  fetchBots,
  fetchStations,
  getChannel,
  getTemplatePreview,
  updateMessage,
  createMessage,
} from "../../stores/thunks";
import { useDebounce } from "../../hooks";
import {
  startCreatingMessage,
  finishEditingMessage,
  updateEditingMessage,
} from "../../stores/slices";
import { FormPage, FormSubmitButtons } from "../../components";
import {
  ActionIcon,
  Badge,
  ComboboxItem,
  Divider,
  Select,
  SimpleGrid,
  Switch,
  Tabs,
  TextInput,
  Title,
  Loader,
  MultiSelect,
  Box,
} from "@mantine/core";
import { useFormHandler, useLookup } from "../../hooks";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { messageEditSchema, MessageEdit, ObjectId } from "../../schemas";
import { Controller } from "react-hook-form";
import { TemplateEditor, LivePreviewPanel } from "./components";
import { LookupSchema } from "../../types";
import { usePageTranslation } from "../../utils";
import { AVAILABLE_LANGUAGES } from "../../i18n";
import { selectMessageEditLoading } from "../../stores/selectors";

type ComponentOwnProps = {
  isEdit: boolean;
};

export const MessageEditPage: FC<ComponentOwnProps> = ({ isEdit }) => {
  const bots = useAppSelector((state) => state.bots.bots);
  const message = useAppSelector((state) => state.messages.editingMessage);
  const templatePreview = useAppSelector(
    (state) => state.messages.templatePreview,
  );
  const previewError = useAppSelector((state) => state.messages.previewError);
  const loading = useAppSelector(selectMessageEditLoading);
  const stationsLoading = useAppSelector((state) => state.stations.loading);
  const dispatch = useAppDispatch();
  const t = usePageTranslation("messages");
  const { messageId } = useParams();

  const messageRef = useRef(message);
  useEffect(() => {
    messageRef.current = message;
  }, [message]);

  const navigate = useNavigate();
  const editOrCreateMessage = useCallback(
    () => dispatch(isEdit ? editMessage(messageId!) : startCreatingMessage()),
    [dispatch, isEdit, messageId],
  );

  useEffect(() => {
    dispatch(fetchBots());
    dispatch(fetchStations());
  }, [dispatch]);

  const getLanguageOptions = useCallback(
    (): ComboboxItem[] =>
      AVAILABLE_LANGUAGES.map((lang) => ({
        key: `lang_${lang}`,
        value: lang,
        label: t(`lang.${lang}`),
      })),
    [t],
  );

  const getBotOptions = useCallback(
    (): ComboboxItem[] =>
      (bots ?? []).map(
        (bot, index) =>
          ({
            key: `bot_${index}`,
            value: bot.id?.toString(),
            label: bot.name,
          }) as ComboboxItem,
      ),
    [bots],
  );

  const { data: stations } = useLookup(LookupSchema.Station, {
    autoFetch: true,
  });

  const getStationOptions = useCallback(
    (): ComboboxItem[] => [
      ...(stations ?? []).map(
        (station, index) =>
          ({
            key: `station_${index}`,
            value: station.value!.toString(),
            label: station.text,
          }) as ComboboxItem,
      ),
    ],
    [stations],
  );

  const handleSave = (data: MessageEdit) => {
    dispatch(updateEditingMessage(data));
    const dispatched = isEdit
      ? dispatch(updateMessage(messageId!))
      : dispatch(createMessage());
    dispatched.unwrap().then(() => navigate(-1));
  };

  const {
    handleFormSubmit,
    hasFieldError,
    renderField,
    registerFormButtons,
    control,
    trigger,
    getControlValue,
    isValid,
  } = useFormHandler<MessageEdit>({
    formKey: "message",
    isEdit: isEdit,
    cleanupAction: () => dispatch(finishEditingMessage()),
    fetchDataAction: editOrCreateMessage,
    saveAction: handleSave,
    validationSchema: messageEditSchema,
    loading: loading || stationsLoading,
    initialData: message,
    fields: [
      {
        name: "name",
        title: t("columns.name"),
        required: true,
      },
      {
        name: "language",
        title: t("columns.language"),
        required: true,
        render: (context) => {
          return (
            <Controller
              name="language"
              control={context.helpers.control}
              defaultValue={"en"}
              render={({ field }) => (
                <Select
                  required
                  allowDeselect={false}
                  data={getLanguageOptions()}
                  {...field}
                  label={context.title}
                  leftSection={stationsLoading ? <Loader size="xs" /> : null}
                  value={field.value?.toString() ?? ""}
                  error={context.helpers.getFieldError("language")}
                  onChange={(value) =>
                    context.helpers.setControlValue(
                      "language",
                      value!,
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
      {
        name: "enabled",
        title: t("columns.enabled"),
        render: (context) => {
          const cbProps = {
            ...context.helpers.registerControl("enabled"),
            onChange: (e: ChangeEvent<HTMLInputElement>) =>
              context.helpers.setControlValue(
                "enabled",
                e.target.checked,
                true,
              ),
            checked:
              (context.helpers.getControlValue("enabled") as boolean) ?? false,
          };
          return <Switch pb="xs" label={context.title} {...cbProps} />;
        },
      },
      {
        name: "botId",
        title: t("columns.bot"),
        required: true,
        render: (context) => {
          return (
            <Controller
              name="botId"
              control={context.helpers.control}
              defaultValue={"0"}
              render={({ field }) => (
                <Select
                  required
                  allowDeselect={false}
                  data={getBotOptions()}
                  {...field}
                  label={context.title}
                  leftSection={stationsLoading ? <Loader size="xs" /> : null}
                  value={field.value?.toString() ?? ""}
                  error={context.helpers.getFieldError("botId")}
                  onChange={(value) =>
                    context.helpers.setControlValue(
                      "botId",
                      value!,
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
      {
        name: "stations",
        title: t("columns.stations"),
        required: true,
        render: (context) => {
          return (
            <Controller
              name="stations"
              control={context.helpers.control}
              defaultValue={[]}
              render={({ field }) => (
                <MultiSelect
                  required
                  data={getStationOptions()}
                  {...field}
                  label={context.title}
                  value={field.value ?? []}
                  error={context.helpers.getFieldError("stations")}
                  styles={{
                    pill: {
                      backgroundColor: "var(--mantine-primary-color-filled)",
                      color: "white",
                      fontWeight: 700,
                    },
                  }}
                  onChange={(value) => {
                    context.helpers.setControlValue(
                      "stations",
                      value,
                      true,
                      false,
                    );
                  }}
                />
              )}
            />
          );
        },
      },
      {
        name: "channelId",
        title: t("columns.channel"),
        required: true,
        render: (context) => {
          const channelId = context.helpers.getControlValue(
            "channelId",
          ) as string;
          const botId = context.helpers.getControlValue("botId") as ObjectId;
          return (
            <TextInput
              mt="sm"
              {...context.helpers.registerControl("channelId")}
              label={context.title}
              rightSection={
                <ActionIcon
                  onClick={() => dispatch(getChannel({ channelId, botId }))}
                >
                  <FontAwesomeIcon icon="search" />
                </ActionIcon>
              }
            />
          );
        },
      },
    ],
    defaultRender: (name, title, context) => (
      <TextInput
        {...context.helpers.registerControl(name)}
        label={title}
        pb="sm"
      />
    ),
  });

  const { setHeaderText } = useHeaderContent();

  useEffect(() => {
    const headerText = isEdit
      ? t("header.editing", { name: message?.name ?? "" })
      : t("header.creating");
    setHeaderText(headerText);
    return () => setHeaderText("");
  }, [isEdit, message?.name, setHeaderText, t]);

  const createTemplateTab = useCallback(
    (
      name:
        | "templateMacros"
        | "messageTemplate"
        | "timeoutTemplate"
        | "shouldSendTemplate",
      title: string,
    ) => {
      return (
        <Tabs.Tab
          key={`template_tab_${name}`}
          value={name}
          rightSection={
            hasFieldError(name) ? (
              <FontAwesomeIcon icon="exclamation-circle" color="red" />
            ) : null
          }
        >
          {title}
        </Tabs.Tab>
      );
    },
    [hasFieldError],
  );

  const [livePreviewLoading, setLivePreviewLoading] = useState(false);

  const refreshLivePreview = useCallback(() => {
    const name = getControlValue("name") as string;
    const stations = getControlValue("stations") as ObjectId[];
    const templateMacros = getControlValue("templateMacros") as string;
    const shouldSendTemplate = getControlValue("shouldSendTemplate") as string;
    const timeoutTemplate = getControlValue("timeoutTemplate") as string;
    const messageTemplate = getControlValue("messageTemplate") as string;
    const language = getControlValue("language") as string;

    setLivePreviewLoading(true);
    dispatch(
      getTemplatePreview({
        id: isEdit ? messageId : undefined,
        name,
        stations,
        templateMacros,
        shouldSendTemplate,
        timeoutTemplate,
        messageTemplate,
        language,
      }),
    ).then(() => {
      setLivePreviewLoading(false);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dispatch, isEdit, messageId]);

  const debouncedRefreshLivePreview = useDebounce(refreshLivePreview, 500);

  const handleTemplateChange = useCallback(() => {
    debouncedRefreshLivePreview();
  }, [debouncedRefreshLivePreview]);

  useEffect(() => {
    if (isEdit && isValid) {
      const timer = setTimeout(() => {
        refreshLivePreview();
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isEdit, isValid, refreshLivePreview]);

  const createTemplateTabPanel = useCallback(
    (
      name:
        | "templateMacros"
        | "messageTemplate"
        | "timeoutTemplate"
        | "shouldSendTemplate",
    ) => {
      return (
        <Tabs.Panel value={name} key={`template_tab_pnl_${name}`}>
          <TemplateEditor
            name={name}
            control={control}
            trigger={trigger}
            onChange={handleTemplateChange}
          />
        </Tabs.Panel>
      );
    },
    [control, trigger, handleTemplateChange],
  );

  const tabs = useMemo(
    () => [
      createTemplateTab("templateMacros", t("templates.macros")),
      createTemplateTab("shouldSendTemplate", t("templates.shouldSend")),
      createTemplateTab("timeoutTemplate", t("templates.timeout")),
      createTemplateTab("messageTemplate", t("templates.message")),
    ],
    [createTemplateTab, t],
  );
  const tabPanels = useMemo(
    () => [
      createTemplateTabPanel("templateMacros"),
      createTemplateTabPanel("shouldSendTemplate"),
      createTemplateTabPanel("timeoutTemplate"),
      createTemplateTabPanel("messageTemplate"),
    ],
    [createTemplateTabPanel],
  );

  return (
    <FormPage loading={loading}>
      <form onSubmit={handleFormSubmit}>
        <SimpleGrid cols={{ xs: 1, sm: 2 }}>
          <Box>
            {renderField("enabled")}
            <SimpleGrid cols={{ xs: 1, sm: 2 }} mt="xs" mb="xs">
              {renderField("name")}
              {renderField("language")}
            </SimpleGrid>
            <Divider />
            <SimpleGrid cols={{ xs: 1, sm: 2 }} mt="xs" mb="xs">
              {renderField("botId")}
              {renderField("stations")}
            </SimpleGrid>
            <Divider />
            <SimpleGrid cols={{ xs: 1, sm: 2 }} mt="xs" mb="xs">
              {renderField("channelId")}
            </SimpleGrid>
            <Badge>{message?.channelName ?? ""}</Badge>
            <Divider mt="xs" mb="xs" />
            <Title order={4}>{t("templates.message")}</Title>
          </Box>
          <LivePreviewPanel
            name={getControlValue("name") as string}
            preview={templatePreview}
            loading={livePreviewLoading}
            error={previewError}
            onRefresh={refreshLivePreview}
            t={t}
            isValid={isValid}
          />
        </SimpleGrid>
        <Tabs
          defaultValue={`messageTemplate`}
          mt="sm"
          mb="xs"
          keepMounted
          keepMountedMode="display-none"
        >
          <Tabs.List mb="xs">{tabs}</Tabs.List>
          {tabPanels}
        </Tabs>
        <FormSubmitButtons {...registerFormButtons()} />
      </form>
    </FormPage>
  );
};
