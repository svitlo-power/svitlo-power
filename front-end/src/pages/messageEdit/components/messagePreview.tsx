import { FC, useMemo } from "react";
import { TemplatePreview } from "../../../stores/types";
import { Group, Badge, Paper, ScrollArea, Text, Button, Tabs } from "@mantine/core";
import { EditorView } from "@codemirror/view";
import ReactCodeMirror, { StateEffect } from '@uiw/react-codemirror';
import { langs } from '@uiw/codemirror-extensions-langs';
import { foldEffect, syntaxTree } from "@codemirror/language";
import Markdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import { TFunction } from "i18next";
import { formatDateTime } from "../../../utils";

type MessagePreviewProps = {
  handleClose: () => void;
  preview: TemplatePreview;
  t: TFunction;
};

export const MessagePreview: FC<MessagePreviewProps> = ({ handleClose, preview, t }) => {
  const yes = t('button.yes');
  const no = t('button.no');
  const data = preview?.data;
  const hasData = data !== undefined && data !== null;

  const jsonExtensions = useMemo(
    () => [langs.json()],
    []
  );

  const jsonContent = useMemo(
    () => JSON.stringify(data, null, 2),
    [data]
  );

  const collapseJson = (view: EditorView) => {
    const effects: StateEffect<{ from: number; to: number; }>[] = [];

    syntaxTree(view.state).iterate({
      enter(node) {
        if (node.from === 0) {
          return;
        }

        if (node.name === "Object" || node.name === "Array") {
          effects.push(
            foldEffect.of({
              from: node.from,
              to: node.to,
            })
          );
        }
      },
    });

    if (effects.length) {
      view.dispatch({ effects });
    }
  };

  return <>
    <Group>
      <Text fw={500}>{t('previewLabels.shouldSend')}</Text>
      <Badge color={(preview?.shouldSend ?? false) ? 'teal' : 'orange'}>{(preview?.shouldSend ?? false) ? yes : no}</Badge>
    </Group>
    <Group>
      <Text fw={500}>{t('previewLabels.timeout')}</Text>
      <Badge>{preview?.timeout}</Badge>
    </Group>
    <Group>
      <Text fw={500}>{t('previewLabels.nextSendTime')}</Text>
      <Badge>{formatDateTime(preview?.nextSendTime)}</Badge>
    </Group>
    <Tabs defaultValue="message">
      <Tabs.List>
        <Tabs.Tab value="message">{t('previewLabels.message')}</Tabs.Tab>
        <Tabs.Tab value="data" disabled={!hasData}>{t('previewLabels.data')}</Tabs.Tab>
      </Tabs.List>
      <Tabs.Panel value="message">
        <Paper withBorder radius="md" p="sm">
          <ScrollArea>
            <Markdown remarkPlugins={[remarkGfm, remarkBreaks]}>{preview?.message ?? ''}</Markdown>
          </ScrollArea>
        </Paper>
      </Tabs.Panel>
      <Tabs.Panel value="data">
        <ScrollArea>
          <Text fw={500} mb="xs">{t('previewLabels.templateData')}</Text>
          <ReactCodeMirror
            theme={"dark"}
            value={jsonContent}
            height="300px"
            extensions={jsonExtensions}
            editable={false}
            onCreateEditor={(view) => {
              collapseJson(view);
            }}
          />
        </ScrollArea>
      </Tabs.Panel>
    </Tabs>
    <Group justify="flex-end">
      <Button variant="default" onClick={handleClose}>{t('button.close')}</Button>
    </Group>
  </>;
}