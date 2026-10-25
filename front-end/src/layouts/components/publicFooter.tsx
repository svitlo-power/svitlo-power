import { Anchor, Box, Group, SimpleGrid, Stack } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { Authors } from "./authors";
import { VisitTracker } from "./visitTracker";
import { VersionDisplay } from "./versionDisplay";

export const PublicFooter = () => {
  const { t } = useTranslation("privacyPolicy");
  const currentYear = new Date().getFullYear();

  return (
    <SimpleGrid
      h="100%"
      verticalSpacing={0}
      spacing={0}
      p={0}
      ta="center"
      cols={{ base: 1, md: 3 }}
      style={{ alignItems: "center" }}
    >
      <Authors />
      <Stack gap={0} align="center" justify="center">
        <Group gap={6} justify="center" align="center">
          <Anchor href="/privacy-policy" size="xs">{t("title")}</Anchor>
          <Box fz="xs">|</Box>
          <Box fz="xs">© Svitlo Power {currentYear}</Box>
        </Group>
        <VersionDisplay compact />
      </Stack>
      <VisitTracker />
    </SimpleGrid>
  );
};
