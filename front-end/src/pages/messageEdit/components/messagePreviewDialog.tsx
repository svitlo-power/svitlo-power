import { FC, useEffect } from "react";
import { RootState, useAppDispatch } from "../../../stores/store";
import { getTemplatePreview } from "../../../stores/thunks";
import { TemplatePreview } from "../../../stores/types";
import { Text, Group, Loader, Stack } from '@mantine/core'
import { modals } from '@mantine/modals'
import { connect } from "react-redux";
import { MessagePreview } from "./messagePreview";
import { ObjectId } from "../../../schemas";
import { TFunction } from "i18next";

type OpenMessagePreviewOptions = {
  message_id?: ObjectId;
  name: string,
  stations: ObjectId[];
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
  shouldSendTemplate,
  timeoutTemplate,
  messageTemplate,
  language,
  t,
}: OpenMessagePreviewOptions) {

  type InnerProps = {
    templatePreview?: TemplatePreview;
    loadingPreview: boolean;
    previewError?: string;
    t: TFunction;
  };

  const mapStateToProps = (state: RootState, ownProps: { t: TFunction }): InnerProps => ({
    templatePreview: state.messages.templatePreview,
    loadingPreview: state.messages.loadingPreview,
    previewError: state.messages.previewError,
    t: ownProps.t,
  });

  const Inner: FC<InnerProps> = ({ 
    templatePreview,
    loadingPreview,
    previewError,
    t,
   }) => {
    const dispatch = useAppDispatch();

    useEffect(() => {
      dispatch(getTemplatePreview({
        id: message_id,
        name,
        stations,
        shouldSendTemplate,
        timeoutTemplate,
        messageTemplate,
        language,
      }));
    }, [dispatch]);

    const handleClose = () => {
      if (id) {
        modals.close(id);
      }
    };

    return (
      <Stack gap="xs">
        {loadingPreview ? (
          <Group justify="center"><Loader /></Group>
        ) : (
          <Stack gap="xs">
            {previewError && <Text c="red">{previewError}</Text>}
            {!previewError && <MessagePreview
                handleClose={handleClose}
                preview={templatePreview!}
                t={t}
              />}
          </Stack>
        )}
      </Stack>
    );
  };

  const ConnectedInner = connect(mapStateToProps)(Inner);

  const id: string | undefined = modals.open({
    title: t ? t('preview.title', { name }) : `Message '${name}' preview`,
    centered: true,
    size: 'lg',
    children: <ConnectedInner t={t} />,
  });
}