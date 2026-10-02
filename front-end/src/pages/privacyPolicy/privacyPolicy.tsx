import { Anchor, Container, List, Stack, Text, Title } from "@mantine/core";
import { FC } from "react";
import { useTranslation } from "react-i18next";

type PolicySection = {
  title: string;
  paragraphs: string[];
  items?: string[];
};

export const PrivacyPolicyPage: FC = () => {
  const { t } = useTranslation("privacyPolicy");
  const sections = t("sections", { returnObjects: true }) as PolicySection[];

  return (
    <Container size="md" w="100%" py="xl">
      <Stack gap="xl">
        <Stack gap="xs">
          <Title order={1}>{t("title")}</Title>
          <Text c="dimmed" size="sm">{t("lastUpdated")}</Text>
          <Text>{t("introduction")}</Text>
        </Stack>

        {sections.map((section) => (
          <Stack key={section.title} gap="sm">
            <Title order={2} size="h3">{section.title}</Title>
            {section.paragraphs.map((paragraph) => <Text key={paragraph}>{paragraph}</Text>)}
            {section.items && (
              <List spacing="xs" pl="md">
                {section.items.map((item) => <List.Item key={item}>{item}</List.Item>)}
              </List>
            )}
          </Stack>
        ))}

        <Text>
          {t("contact")}{" "}
          <Anchor href="https://t.me/bearpawmaxim" target="_blank" rel="noreferrer">@bearpawmaxim</Anchor>
          {" "}{t("or")}{" "}
          <Anchor href="https://t.me/gizmoboss" target="_blank" rel="noreferrer">@gizmoboss</Anchor>.
        </Text>
      </Stack>
    </Container>
  );
};