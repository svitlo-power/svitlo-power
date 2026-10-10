import { FC, useCallback, useEffect, useMemo } from "react";
import { connect } from "react-redux";
import { Badge, Code, Group, Paper, SimpleGrid, Stack, Tabs, Text } from "@mantine/core";
import { modals } from "@mantine/modals";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { RootState, useAppDispatch } from "../../stores/store";
import {
  deletePushDevice, fetchPushDevices, fetchPushTopics, sendTestPush, setPushTopicState,
} from "../../stores/thunks";
import { PushDeviceItem, PushTestRequest, PushTopicItem } from "../../stores/types";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType } from "../../types";
import { usePageTranslation } from "../../utils";
import { useRefreshKey } from "../../hooks";
import useLocalStorage from "../../hooks/useLocalStorage";
import { LocalizableValue } from "../../schemas";
import i18n from "../../i18n";
import { openPushTestDialog } from "./components/pushTestDialog";

type ComponentProps = {
  devices: PushDeviceItem[];
  topics: PushTopicItem[];
  loading: boolean;
  error: string | null;
};

const mapStateToProps = (state: RootState): ComponentProps => ({
  devices: state.pushDevices.items,
  topics: state.pushTopics.items,
  loading: state.pushDevices.loading || state.pushTopics.loading,
  error: state.pushDevices.error ?? state.pushTopics.error,
});

const localized = (value: LocalizableValue) =>
  value[i18n.language as keyof LocalizableValue] ?? Object.values(value)[0] ?? "";

const StatTile: FC<{ label: string; value: number }> = ({ label, value }) => (
  <Paper withBorder p="sm" radius="md">
    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>{label}</Text>
    <Text size="xl" fw={700}>{value}</Text>
  </Paper>
);

const Component: FC<ComponentProps> = ({ devices, topics, loading, error }) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation("push");
  const { refreshKey } = useRefreshKey();
  const [tab, setTab] = useLocalStorage<string>("push.tab", "topics");

  const fetchDevices = useCallback(() => {
    dispatch(fetchPushDevices());
  }, [dispatch]);

  const fetchTopics = useCallback(() => {
    dispatch(fetchPushTopics());
  }, [dispatch]);

  useEffect(() => {
    fetchDevices();
    fetchTopics();
  }, [fetchDevices, fetchTopics]);

  const stats = useMemo(() => ({
    total: devices.length,
    android: devices.filter((d) => d.platform === "android").length,
    web: devices.filter((d) => d.platform === "web").length,
    enabled: devices.filter((d) => d.enabled).length,
  }), [devices]);

  const send = useCallback(
    (request: PushTestRequest) => dispatch(sendTestPush(request)).unwrap(),
    [dispatch],
  );

  const openTest = useCallback((device?: PushDeviceItem) => {
    openPushTestDialog({ t, device, enabledCount: stats.enabled, onSend: send });
  }, [t, stats.enabled, send]);

  const openTopicTest = useCallback((topic: PushTopicItem) => {
    openPushTestDialog({
      t,
      topic: { key: topic.key, name: localized(topic.name), subscribers: topic.subscribers },
      enabledCount: stats.enabled,
      onSend: send,
    });
  }, [t, stats.enabled, send]);

  const handleDelete = useCallback((device: PushDeviceItem) => {
    modals.openConfirmModal({
      title: t("modal.deleteTitle"),
      children: t("modal.deleteConfirm"),
      labels: { confirm: t("button.delete"), cancel: t("button.cancel") },
      confirmProps: { color: "red" },
      onConfirm: () => dispatch(deletePushDevice(device.id)).then(() => fetchTopics()),
    });
  }, [dispatch, fetchTopics, t]);

  const getHeaderButtons = useCallback((): PageHeaderButton[] => [
    { text: t("button.sendToAll"), icon: "paper-plane", color: "teal", onClick: () => openTest(), disabled: false },
  ], [openTest, t]);

  const { setHeaderButtons } = useHeaderContent();
  useEffect(() => {
    setHeaderButtons(getHeaderButtons());
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons]);

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <Page loading={loading}>
      <Stack gap="md" style={{ flex: 1 }}>
        <SimpleGrid cols={{ base: 2, sm: 4 }} p="sm" pb={0}>
          <StatTile label={t("stats.total")} value={stats.total} />
          <StatTile label={t("stats.android")} value={stats.android} />
          <StatTile label={t("stats.web")} value={stats.web} />
          <StatTile label={t("stats.enabled")} value={stats.enabled} />
        </SimpleGrid>

        <Tabs value={tab} onChange={(value) => setTab(value ?? "topics")} keepMounted={false}
          style={{ flex: 1, display: "flex", flexDirection: "column" }}>
          <Tabs.List px="sm">
            <Tabs.Tab value="topics" leftSection={<FontAwesomeIcon icon="bell" />}>
              {t("tabs.topics")}
            </Tabs.Tab>
            <Tabs.Tab value="devices" leftSection={<FontAwesomeIcon icon="mobile" />}>
              {t("tabs.devices")}
            </Tabs.Tab>
          </Tabs.List>

          <Tabs.Panel value="topics" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <Text size="sm" c="dimmed" px="sm" pt="sm">{t("topics.hint")}</Text>
            <DataTable<PushTopicItem>
              data={topics}
              fetchAction={fetchTopics}
              refreshKey={refreshKey}
              useFilters={false}
              usePagination={false}
              columns={[
                {
                  id: "name",
                  header: t("topics.name"),
                  cell: ({ row }) => (
                    <Stack gap={0}>
                      <Text size="sm" fw={600}>{localized(row.original.name)}</Text>
                      <Text size="xs" c="dimmed">{localized(row.original.description)}</Text>
                    </Stack>
                  ),
                },
                {
                  id: "key",
                  header: t("topics.key"),
                  accessorKey: "key",
                  cell: ({ row }) => <Code>{row.original.key}</Code>,
                },
                {
                  id: "subscribers",
                  header: t("topics.subscribers"),
                  accessorKey: "subscribers",
                  enableSorting: true,
                  meta: {
                    dataType: ColumnDataType.Number,
                  },
                },
                {
                  id: "enabled",
                  header: t("topics.enabled"),
                  accessorKey: "enabled",
                  enableSorting: true,
                  meta: {
                    dataType: ColumnDataType.Boolean,
                    readOnly: false,
                    checkedChange: (row, state) => dispatch(setPushTopicState({ key: row.key, enabled: state })),
                  },
                },
                {
                  id: "actions",
                  meta: {
                    dataType: "actions",
                    actions: [
                      {
                        icon: "paper-plane",
                        color: "teal",
                        text: t("actions.sendTestTopic"),
                        onlyIcon: true,
                        clickHandler: (row) => openTopicTest(row),
                      },
                    ],
                  },
                },
              ]}
              tableKey="pushTopics"
            />
          </Tabs.Panel>

          <Tabs.Panel value="devices" style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            <DataTable<PushDeviceItem>
              data={devices}
              fetchAction={fetchDevices}
              refreshKey={refreshKey}
              useFilters={false}
              usePagination={false}
              columns={[
                {
                  id: "platform",
                  header: t("table.platform"),
                  accessorKey: "platform",
                  enableSorting: true,
                  cell: ({ row }) => (
                    <Group gap={6}>
                      <FontAwesomeIcon icon={row.original.platform === "android" ? "mobile" : "globe"} />
                      <Text size="sm">{t(`platform.${row.original.platform}`)}</Text>
                    </Group>
                  ),
                  meta: {
                    dataType: ColumnDataType.Text,
                  },
                },
                {
                  id: "language",
                  header: t("table.language"),
                  accessorKey: "language",
                  enableSorting: true,
                  cell: ({ row }) => <Badge variant="light" color="gray">{row.original.language}</Badge>,
                  meta: {
                    dataType: ColumnDataType.Text,
                  },
                },
                {
                  id: "appVersion",
                  header: t("table.appVersion"),
                  accessorKey: "appVersion",
                  enableSorting: true,
                  meta: {
                    dataType: ColumnDataType.Text,
                  },
                },
                {
                  id: "enabled",
                  header: t("table.enabled"),
                  accessorKey: "enabled",
                  enableSorting: true,
                  meta: {
                    dataType: ColumnDataType.Boolean,
                  },
                },
                {
                  id: "subscriptions",
                  header: t("table.subscriptions"),
                  cell: ({ row }) => {
                    const off = row.original.disabledTopics.length;
                    return off === 0
                      ? <Text size="sm">{t("subscriptions")}</Text>
                      : <Text size="sm" c="orange">{t("subscriptionsPartial", { count: off })}</Text>;
                  },
                },
                {
                  id: "createdAt",
                  header: t("table.createdAt"),
                  accessorKey: "createdAt",
                  enableSorting: true,
                  meta: {
                    dataType: ColumnDataType.DateTime,
                  },
                },
                {
                  id: "lastSeen",
                  header: t("table.lastSeen"),
                  accessorKey: "lastSeen",
                  enableSorting: true,
                  meta: {
                    dataType: ColumnDataType.DateTime,
                  },
                },
                {
                  id: "actions",
                  meta: {
                    dataType: "actions",
                    actions: [
                      {
                        icon: "paper-plane",
                        color: "teal",
                        text: t("actions.sendTest"),
                        onlyIcon: true,
                        clickHandler: (row) => openTest(row),
                      },
                      {
                        icon: "trash",
                        color: "red",
                        text: t("actions.delete"),
                        onlyIcon: true,
                        clickHandler: (row) => handleDelete(row),
                      },
                    ],
                  },
                },
              ]}
              tableKey="pushDevices"
            />
          </Tabs.Panel>
        </Tabs>
      </Stack>
    </Page>
  );
};

export const PushPage = connect(mapStateToProps)(Component);
