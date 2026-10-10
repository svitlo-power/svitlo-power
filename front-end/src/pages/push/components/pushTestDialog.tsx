import { FC, useState } from "react";
import { TFunction } from "i18next";
import { modals } from "@mantine/modals";
import { Alert, Autocomplete, Button, Group, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { PushDeviceItem, PushSendResult, PushTestRequest } from "../../../stores/types";

// Screens of the mobile app that a notification can open.
const APP_ROUTES = ["/", "/schedule", "/stats", "/settings"];

export type PushTestTopic = {
  key: string;
  name: string;
  subscribers: number;
};

type OpenPushTestOptions = {
  t: TFunction;
  device?: PushDeviceItem;
  topic?: PushTestTopic;
  enabledCount: number;
  onSend: (request: PushTestRequest) => Promise<PushSendResult>;
};

export function openPushTestDialog({ t, device, topic, enabledCount, onSend }: OpenPushTestOptions) {
  const Inner: FC = () => {
    const [title, setTitle] = useState("");
    const [body, setBody] = useState("");
    const [route, setRoute] = useState("/");
    const [touched, setTouched] = useState(false);
    const [sending, setSending] = useState(false);
    const [result, setResult] = useState<PushSendResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    const routeValid = route === "" || (route.startsWith("/") && !route.startsWith("//"));
    const valid = title.trim() !== "" && body.trim() !== "" && routeValid;

    const handleSend = async () => {
      setTouched(true);
      if (!valid) return;

      setSending(true);
      setError(null);
      try {
        setResult(await onSend({
          title: title.trim(),
          body: body.trim(),
          route: route || undefined,
          deviceId: device?.id,
          topic: topic?.key,
        }));
      } catch (e: unknown) {
        setResult(null);
        setError(typeof e === "string" ? e : String((e as Error)?.message ?? e));
      } finally {
        setSending(false);
      }
    };

    return (
      <Stack>
        <Text size="sm" c="dimmed">
          {topic
            ? t("test.targetTopic", { count: topic.subscribers })
            : device
              ? t("test.targetDevice", { platform: t(`platform.${device.platform}`), language: device.language })
              : t("test.targetAll", { count: enabledCount })}
        </Text>
        <TextInput
          label={t("test.fieldTitle")}
          value={title}
          onChange={(e) => setTitle(e.currentTarget.value)}
          error={touched && !title.trim() ? t("test.required") : undefined}
          maxLength={100}
          withAsterisk
          data-autofocus
        />
        <Textarea
          label={t("test.fieldBody")}
          value={body}
          onChange={(e) => setBody(e.currentTarget.value)}
          error={touched && !body.trim() ? t("test.required") : undefined}
          minRows={3}
          autosize
          maxLength={500}
          withAsterisk
        />
        <Autocomplete
          label={t("test.fieldRoute")}
          description={t("test.fieldRouteDescription")}
          data={APP_ROUTES}
          value={route}
          onChange={setRoute}
          error={!routeValid ? t("test.routeInvalid") : undefined}
        />

        {result && (
          <Alert color={result.failureCount ? "yellow" : "green"} title={t("test.resultTitle")}
            icon={<FontAwesomeIcon icon="check" />}>
            {t("test.result", {
              success: result.successCount,
              failure: result.failureCount,
              removed: result.removedCount,
            })}
          </Alert>
        )}
        {error && (
          <Alert color="red" title={t("test.errorTitle")} icon={<FontAwesomeIcon icon="triangle-exclamation" />}>
            {error}
          </Alert>
        )}

        <Group justify="flex-end" gap="xs">
          <Button variant="default" onClick={() => modals.close(id)}>
            {t("button.close")}
          </Button>
          <Button onClick={handleSend} loading={sending} leftSection={<FontAwesomeIcon icon="paper-plane" />}
            disabled={topic ? topic.subscribers === 0 : !device && enabledCount === 0}>
            {result ? t("button.sendAgain") : t("button.send")}
          </Button>
        </Group>
      </Stack>
    );
  };

  const id: string = modals.open({
    title: topic
      ? t("test.titleTopic", { name: topic.name })
      : device ? t("test.titleDevice") : t("test.titleAll"),
    centered: true,
    size: "lg",
    children: <Inner />,
  });
}
