import { FC, useState } from "react";
import { TFunction } from "i18next";
import { modals } from "@mantine/modals";
import { Alert, Button, Group, Stack, Text, TextInput, Textarea } from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { AnnouncementRequest } from "../../../stores/types";
import { CountryFlag } from "../../../components";
import { AVAILABLE_LANGUAGES } from "../../../i18n";

type OpenAnnouncementOptions = {
  t: TFunction;
  onPublish: (request: AnnouncementRequest) => Promise<unknown>;
};

const filled = (values: Record<string, string>) =>
  Object.fromEntries(Object.entries(values).map(([k, v]) => [k, v.trim()]).filter(([, v]) => v));

export function openAnnouncementDialog({ t, onPublish }: OpenAnnouncementOptions) {
  const Inner: FC = () => {
    const [title, setTitle] = useState<Record<string, string>>({});
    const [body, setBody] = useState<Record<string, string>>({});
    const [touched, setTouched] = useState(false);
    const [publishing, setPublishing] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Every language that has a title needs a text and vice versa; missing languages fall back to the default one
    const languages = AVAILABLE_LANGUAGES.filter((lang) => title[lang]?.trim() || body[lang]?.trim());
    const incomplete = languages.filter((lang) => !title[lang]?.trim() || !body[lang]?.trim());
    const valid = languages.length > 0 && incomplete.length === 0;

    const handlePublish = async () => {
      setTouched(true);
      if (!valid) return;
      setPublishing(true);
      setError(null);
      try {
        await onPublish({ title: filled(title), body: filled(body) });
        modals.close(id);
      } catch (e: unknown) {
        setError(typeof e === "string" ? e : String((e as Error)?.message ?? e));
      } finally {
        setPublishing(false);
      }
    };

    return (
      <Stack>
        <Text size="sm" c="dimmed">{t("dialog.hint")}</Text>
        {AVAILABLE_LANGUAGES.map((lang) => (
          <Stack key={lang} gap="xs">
            <TextInput
              label={`${t("dialog.title")} (${t(`lang.${lang}`)})`}
              leftSection={<CountryFlag language={lang} />}
              value={title[lang] ?? ""}
              onChange={(e) => setTitle({ ...title, [lang]: e.currentTarget.value })}
              error={touched && incomplete.includes(lang) && !title[lang]?.trim() ? t("dialog.required") : undefined}
              maxLength={100}
            />
            <Textarea
              label={`${t("dialog.body")} (${t(`lang.${lang}`)})`}
              value={body[lang] ?? ""}
              onChange={(e) => setBody({ ...body, [lang]: e.currentTarget.value })}
              error={touched && incomplete.includes(lang) && !body[lang]?.trim() ? t("dialog.required") : undefined}
              minRows={3}
              autosize
              maxLength={500}
            />
          </Stack>
        ))}

        {touched && languages.length === 0 && (
          <Alert color="red">{t("dialog.empty")}</Alert>
        )}
        {error && (
          <Alert color="red" icon={<FontAwesomeIcon icon="triangle-exclamation" />}>{error}</Alert>
        )}

        <Group justify="flex-end" gap="xs">
          <Button variant="default" onClick={() => modals.close(id)}>
            {t("button.cancel")}
          </Button>
          <Button onClick={handlePublish} loading={publishing} leftSection={<FontAwesomeIcon icon="paper-plane" />}>
            {t("button.publish")}
          </Button>
        </Group>
      </Stack>
    );
  };

  const id: string = modals.open({
    title: t("dialog.header"),
    centered: true,
    size: "lg",
    children: <Inner />,
  });
}
