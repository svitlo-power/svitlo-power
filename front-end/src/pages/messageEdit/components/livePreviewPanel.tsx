import { FC } from "react";
import {
  Box,
  Button,
  Divider,
  Group,
  LoadingOverlay,
  Paper,
  ScrollArea,
  Stack,
  Text,
} from "@mantine/core";
import { MessagePreview } from "./messagePreview";
import { TemplatePreview } from "../../../stores/types";
import { TFunction } from "i18next";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";

type LivePreviewPanelProps = {
  name: string;
  preview?: TemplatePreview;
  loading: boolean;
  error?: string;
  isValid: boolean;
  onRefresh: () => void;
  t: TFunction;
};

export const LivePreviewPanel: FC<LivePreviewPanelProps> = ({
  name,
  preview,
  loading,
  error,
  isValid,
  onRefresh,
  t,
}) => {
  return (
    <Paper withBorder p="xs" radius="md">
      <Box pos="relative" h="100%">
        <LoadingOverlay
          visible={loading || !isValid || !!error}
          loaderProps={{
            children: (
              <Box ta={'center'} m='lg'>
                {!isValid && (
                  <Text c="dimmed">{t("livePreview.invalidForm")}</Text>
                )}
                {error && (
                  <Text c="red">{t("livePreview.error", { error })}</Text>
                )}
              </Box>
            ),
          }}
          overlayProps={{
            radius: "sm",
            blur: 4,
            ...(error && { style: { backgroundColor: "rgba(255, 0, 0, 0.15)" } }),
          }}
        />
        {!loading && isValid && !error && preview && (
          <Stack gap="xs">
            <Group justify="space-between" align="center">
              <Text fw={500}>{t("preview.title", { name: name })}</Text>
            </Group>
            <ScrollArea styles={{ scrollbar: { width: 8 } }}>
              <MessagePreview preview={preview} t={t} />
              <Divider mt={"sm"} mb={"sm"} />
              <Group justify="end">
                <Button
                  onClick={onRefresh}
                  leftSection={<FontAwesomeIcon icon="refresh" />}
                >
                  {t("button.refresh")}
                </Button>
              </Group>
            </ScrollArea>
          </Stack>
        )}
      </Box>
    </Paper>
  );
};
