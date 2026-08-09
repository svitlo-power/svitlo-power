import { FC } from "react";
import { TemplatePreview } from "../../../stores/types";
import { Group, Badge, Paper, ScrollArea, Text, Button, Tabs, Table } from "@mantine/core";
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
  const requests = (preview?.data?.requests as Array<Record<string, unknown>> | undefined) ?? [];
  const hasData = requests.length > 0;
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
          <ScrollArea style={{ maxHeight: 400 }}>
            <Markdown remarkPlugins={[remarkGfm, remarkBreaks]}>{preview?.message ?? ''}</Markdown>
          </ScrollArea>
        </Paper>
      </Tabs.Panel>
      <Tabs.Panel value="data">
        <Paper withBorder radius="md" p="sm">
          <ScrollArea style={{ maxHeight: 400 }}>
            <Table>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t('previewLabels.request')}</Table.Th>
                  <Table.Th>{t('previewLabels.value')}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {requests.map((item, index) => (
                  <Table.Tr key={index}>
                    <Table.Td>{String(item.request ?? '')}</Table.Td>
                    <Table.Td>{String(item.value ?? '')}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </ScrollArea>
        </Paper>
      </Tabs.Panel>
    </Tabs>
    <Group justify="flex-end">
      <Button variant="default" onClick={handleClose}>{t('button.close')}</Button>
    </Group>
  </>;
}