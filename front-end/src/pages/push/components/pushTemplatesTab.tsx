import { FC, useCallback, useEffect, useMemo, useState } from "react";
import { TFunction } from "i18next";
import {
  Accordion, Alert, Badge, Button, Code, Grid, Group, NavLink, NumberInput, Paper, ScrollArea, Select,
  SegmentedControl, Stack, Switch, Text, Title,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { modals } from "@mantine/modals";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useAppDispatch } from "../../../stores/store";
import {
  fetchPushTemplates, previewPushTemplate, resetPushTemplate, savePushTemplate, testPushTemplate,
} from "../../../stores/thunks";
import {
  PushDeviceItem, PushTemplateItem, PushTemplatePreview, PushTemplateRequest, PushTopicItem,
} from "../../../stores/types";
import { LocalizableValue } from "../../../schemas";
import { CountryFlag, JinjaEditor } from "../../../components";
import { AVAILABLE_LANGUAGES } from "../../../i18n";
import { templateVariablesFromSample } from "../../../utils";

// Variables every template gets in addition to the event's own
const COMMON_VARIABLES = ["lang", "topic", "now"];

type ComponentProps = {
  t: TFunction;
  templates: PushTemplateItem[];
  topics: PushTopicItem[];
  devices: PushDeviceItem[];
  localized: (value: LocalizableValue) => string;
};

const toRequest = (template: PushTemplateItem): PushTemplateRequest => ({
  enabled: template.enabled,
  title: { ...template.title },
  body: { ...template.body },
  route: template.route,
  shouldSend: template.shouldSend,
  macros: template.macros,
  params: Object.fromEntries(template.params.map((p) => [p.key, p.value])),
});

const errorText = (e: unknown) => (typeof e === "string" ? e : String((e as Error)?.message ?? e));

const PreviewPanel: FC<{ t: TFunction; preview: PushTemplatePreview | null; error: string | null }> = (
  { t, preview, error },
) => {
  if (error) {
    return <Alert color="red" icon={<FontAwesomeIcon icon="triangle-exclamation" />}>{error}</Alert>;
  }
  if (!preview) {
    return null;
  }
  return (
    <Stack gap="xs">
      {preview.shouldSendError
        ? <Alert color="red" title={t("templates.condition")}>{preview.shouldSendError}</Alert>
        : (
          <Badge color={preview.shouldSend ? "teal" : "gray"} variant="light">
            {preview.shouldSend ? t("templates.willSend") : t("templates.willSkip")}
          </Badge>
        )}
      {preview.items.map((item) => (
        <Paper key={item.language} withBorder p="sm" radius="md">
          <Group gap={6} mb={4}>
            <CountryFlag language={item.language} />
            <Text size="xs" c="dimmed">{t(`lang.${item.language}`)}</Text>
          </Group>
          {item.error
            ? <Text size="sm" c="red">{item.error}</Text>
            : (
              <>
                <Text size="sm" fw={700}>{item.title}</Text>
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>{item.body}</Text>
                {item.route && <Code>{item.route}</Code>}
              </>
            )}
        </Paper>
      ))}
    </Stack>
  );
};

const TemplateEditorPanel: FC<{
  t: TFunction;
  template: PushTemplateItem;
  devices: PushDeviceItem[];
  name: string;
  description: string;
}> = ({ t, template, devices, name, description }) => {
  const dispatch = useAppDispatch();
  const [form, setForm] = useState<PushTemplateRequest>(() => toRequest(template));
  const [language, setLanguage] = useState(AVAILABLE_LANGUAGES[0]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ color: string; text: string } | null>(null);
  const [preview, setPreview] = useState<PushTemplatePreview | null>(null);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  // Saving or resetting replaces the template in the store; the form follows it
  const [source, setSource] = useState(template);
  if (source !== template) {
    setSource(template);
    setForm(toRequest(template));
  }

  const variables = useMemo(
    () => templateVariablesFromSample(template.variables, COMMON_VARIABLES),
    [template.variables],
  );
  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(toRequest(template)), [form, template]);

  const [debouncedForm] = useDebouncedValue(form, 500);
  useEffect(() => {
    let cancelled = false;
    dispatch(previewPushTemplate({ topic: template.topic, request: debouncedForm })).unwrap()
      .then((result) => {
        if (!cancelled) {
          setPreview(result);
          setPreviewError(null);
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setPreviewError(errorText(e));
        }
      });
    return () => { cancelled = true; };
  }, [dispatch, template.topic, debouncedForm]);

  const update = (patch: Partial<PushTemplateRequest>) => {
    setForm((current) => ({ ...current, ...patch }));
    setMessage(null);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await dispatch(savePushTemplate({ topic: template.topic, request: form })).unwrap();
      setMessage({ color: "green", text: t("templates.saved") });
    } catch (e) {
      setMessage({ color: "red", text: errorText(e) });
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    modals.openConfirmModal({
      title: t("templates.resetTitle"),
      children: t("templates.resetConfirm"),
      labels: { confirm: t("templates.reset"), cancel: t("button.cancel") },
      confirmProps: { color: "red" },
      onConfirm: () => {
        dispatch(resetPushTemplate(template.topic)).unwrap()
          .then(() => setMessage({ color: "green", text: t("templates.resetDone") }))
          .catch((e) => setMessage({ color: "red", text: errorText(e) }));
      },
    });
  };

  const handleTest = async () => {
    if (!deviceId) return;
    setTesting(true);
    try {
      const result = await dispatch(testPushTemplate({ topic: template.topic, deviceId, request: form })).unwrap();
      setMessage({
        color: result.failureCount ? "yellow" : "green",
        text: t("test.result", {
          success: result.successCount, failure: result.failureCount, removed: result.removedCount,
        }),
      });
    } catch (e) {
      setMessage({ color: "red", text: errorText(e) });
    } finally {
      setTesting(false);
    }
  };

  const deviceOptions = devices.filter((d) => d.enabled).map((d) => ({
    value: d.id,
    label: `${t(`platform.${d.platform}`)} · ${d.language}${d.appVersion ? ` · ${d.appVersion}` : ""}`
      + ` · ${new Date(d.lastSeen).toLocaleString()}`,
  }));

  return (
    <Stack gap="md">
      <Group justify="space-between" align="flex-start" wrap="nowrap">
        <Stack gap={2}>
          <Group gap="xs">
            <Title order={4}>{name}</Title>
            <Code>{template.topic}</Code>
          </Group>
          <Text size="sm" c="dimmed">{description}</Text>
        </Stack>
        <Switch
          label={t("templates.enabled")}
          checked={form.enabled}
          onChange={(e) => update({ enabled: e.currentTarget.checked })}
        />
      </Group>

      {message && (
        <Alert color={message.color} withCloseButton onClose={() => setMessage(null)}>{message.text}</Alert>
      )}

      <Grid gap="md">
        <Grid.Col span={{ base: 12, lg: 7 }}>
          <Stack gap="sm">
            <SegmentedControl
              value={language}
              onChange={setLanguage}
              data={AVAILABLE_LANGUAGES.map((lang) => ({
                value: lang,
                label: (
                  <Group gap={6} justify="center" wrap="nowrap">
                    <CountryFlag language={lang} />
                    <span>{t(`lang.${lang}`)}</span>
                  </Group>
                ),
              }))}
            />
            <JinjaEditor
              key={`title-${language}`}
              label={t("templates.title")}
              value={form.title[language] ?? ""}
              onChange={(value) => update({ title: { ...form.title, [language]: value } })}
              variables={variables}
            />
            <JinjaEditor
              key={`body-${language}`}
              label={t("templates.body")}
              description={t("templates.languageFallback")}
              value={form.body[language] ?? ""}
              onChange={(value) => update({ body: { ...form.body, [language]: value } })}
              variables={variables}
              minHeight="80px"
            />
            <JinjaEditor
              label={t("templates.route")}
              description={t("templates.routeDescription")}
              value={form.route}
              onChange={(value) => update({ route: value })}
              variables={variables}
            />

            {template.params.length > 0 && (
              <Group grow align="flex-start">
                {template.params.map((param) => (
                  <NumberInput
                    key={param.key}
                    label={t(`templates.params.${param.key}`)}
                    description={t("templates.paramDefault", { value: param.default })}
                    min={param.min}
                    max={param.max}
                    value={form.params[param.key] ?? param.value}
                    onChange={(value) => update({
                      params: { ...form.params, [param.key]: typeof value === "number" ? value : param.default },
                    })}
                  />
                ))}
              </Group>
            )}

            <Accordion variant="contained" multiple>
              <Accordion.Item value="condition">
                <Accordion.Control icon={<FontAwesomeIcon icon="code" />}>{t("templates.condition")}</Accordion.Control>
                <Accordion.Panel>
                  <JinjaEditor
                    description={t("templates.conditionDescription")}
                    value={form.shouldSend ?? ""}
                    onChange={(value) => update({ shouldSend: value || null })}
                    variables={variables}
                  />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="macros">
                <Accordion.Control icon={<FontAwesomeIcon icon="terminal" />}>{t("templates.macros")}</Accordion.Control>
                <Accordion.Panel>
                  <JinjaEditor
                    description={t("templates.macrosDescription")}
                    value={form.macros ?? ""}
                    onChange={(value) => update({ macros: value || null })}
                    variables={variables}
                    minHeight="80px"
                  />
                </Accordion.Panel>
              </Accordion.Item>
              <Accordion.Item value="variables">
                <Accordion.Control icon={<FontAwesomeIcon icon="file-lines" />}>{t("templates.variables")}</Accordion.Control>
                <Accordion.Panel>
                  <Text size="xs" c="dimmed" mb="xs">{t("templates.variablesDescription")}</Text>
                  <Code block>{JSON.stringify(template.variables, null, 2)}</Code>
                </Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          </Stack>
        </Grid.Col>

        <Grid.Col span={{ base: 12, lg: 5 }}>
          <Stack gap="sm">
            <Text fw={600}>{t("templates.preview")}</Text>
            <PreviewPanel t={t} preview={preview} error={previewError} />
            <Group align="flex-end" wrap="nowrap">
              <Select
                style={{ flex: 1 }}
                label={t("templates.testDevice")}
                placeholder={t("templates.testDevicePlaceholder")}
                data={deviceOptions}
                value={deviceId}
                onChange={setDeviceId}
                searchable
              />
              <Button
                variant="light"
                color="teal"
                onClick={handleTest}
                loading={testing}
                disabled={!deviceId}
                leftSection={<FontAwesomeIcon icon="paper-plane" />}
              >
                {t("button.send")}
              </Button>
            </Group>
          </Stack>
        </Grid.Col>
      </Grid>

      <Group justify="space-between">
        <Button variant="subtle" color="red" onClick={handleReset} leftSection={<FontAwesomeIcon icon="refresh" />}>
          {t("templates.reset")}
        </Button>
        <Group gap="xs">
          <Button variant="default" disabled={!dirty} onClick={() => setForm(toRequest(template))}>
            {t("button.cancel")}
          </Button>
          <Button onClick={handleSave} loading={saving} disabled={!dirty} leftSection={<FontAwesomeIcon icon="save" />}>
            {t("button.save")}
          </Button>
        </Group>
      </Group>
    </Stack>
  );
};

export const PushTemplatesTab: FC<ComponentProps> = ({ t, templates, topics, devices, localized }) => {
  const dispatch = useAppDispatch();
  const [selected, setSelected] = useState<string | null>(null);

  const fetchTemplates = useCallback(() => {
    dispatch(fetchPushTemplates());
  }, [dispatch]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const current = templates.find((tpl) => tpl.topic === selected) ?? templates[0];
  const currentTopic = topics.find((tp) => tp.key === current?.topic);
  const topicName = (key: string) => {
    const topic = topics.find((tp) => tp.key === key);
    return topic ? localized(topic.name) : key;
  };

  return (
    <Grid gap="md" p="sm">
      <Grid.Col span={{ base: 12, md: 3 }}>
        <Text size="sm" c="dimmed" mb="xs">{t("templates.hint")}</Text>
        <ScrollArea.Autosize mah="70vh">
          {templates.map((template) => {
            const topic = topics.find((tp) => tp.key === template.topic);
            const off = !template.enabled || (topic && !topic.enabled);
            return (
              <NavLink
                key={template.topic}
                active={template.topic === current?.topic}
                label={topicName(template.topic)}
                description={template.topic}
                onClick={() => setSelected(template.topic)}
                rightSection={off
                  ? <Badge size="xs" color="gray" variant="light">{t("templates.off")}</Badge>
                  : <Badge size="xs" color="teal" variant="light">{t("templates.on")}</Badge>}
              />
            );
          })}
        </ScrollArea.Autosize>
      </Grid.Col>
      <Grid.Col span={{ base: 12, md: 9 }}>
        {current && (
          <TemplateEditorPanel
            key={current.topic}
            t={t}
            template={current}
            devices={devices}
            name={topicName(current.topic)}
            description={currentTopic ? localized(currentTopic.description) : ""}
          />
        )}
      </Grid.Col>
    </Grid>
  );
};
