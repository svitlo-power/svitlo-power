import { FC, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "../../../stores/store";
import { getTemplatePreview } from "../../../stores/thunks";
import { Text, Group, Loader, Stack } from "@mantine/core";
import { modals } from "@mantine/modals";
import { MessagePreview } from "./messagePreview";
import { ObjectId } from "../../../schemas";
import { TFunction } from "i18next";

type OpenMessagePreviewOptions = {
  message_id?: ObjectId;
  name: string;
  stations: ObjectId[];
  templateMacros: string;
  shouldSendTemplate: string;
  timeoutTemplate: string;
  messageTemplate: string;
  language: string;
  t: TFunction;
};

export function openMessagePreviewDialog({
  message_id,
  name,
  stations,
  templateMacros,
  shouldSendTemplate,
  timeoutTemplate,
  messageTemplate,
  language,
  t,
}: OpenMessagePreviewOptions) {
  const Inner: FC<{ t: TFunction }> = ({ t }) => {
    const templatePreview = useAppSelector(
      (state) => state.messages.templatePreview,
    );
    const loadingPreview = useAppSelector(
      (state) => state.messages.loadingPreview,
    );
    const previewError = useAppSelector((state) => state.messages.previewError);
    const dispatch = useAppDispatch();

    useEffect(() => {
      dispatch(
        getTemplatePreview({
          id: message_id,
          name,
          stations,
          templateMacros,
          shouldSendTemplate,
          timeoutTemplate,
          messageTemplate,
          language,
        }),
      );
    }, [dispatch]);

    const handleClose = () => {
      if (id) {
        modals.close(id);
      }
    };

    return (
      <Stack gap="xs">
        {loadingPreview ? (
          <Group justify="center">
            <Loader />
          </Group>
        ) : (
          <Stack gap="xs">
            {previewError && <Text c="red">{previewError}</Text>}
            {!previewError && (
              <MessagePreview
                handleClose={handleClose}
                preview={templatePreview!}
                t={t}
              />
            )}
          </Stack>
        )}
      </Stack>
    );
  };

  const id: string | undefined = modals.open({
    title: t ? t("preview.title", { name }) : `Message '${name}' preview`,
    centered: true,
    size: "lg",
    children: <Inner t={t} />,
  });
}
