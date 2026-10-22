import { FC, useCallback } from "react";
import { TFunction } from "i18next";
import { Badge, Group, Stack, Text, Tooltip } from "@mantine/core";
import { useAppDispatch } from "../../../stores/store";
import { fetchPushDeliveries } from "../../../stores/thunks";
import { PushDeliveryItem, PushDeliveryStatus } from "../../../stores/types";
import { DataTable } from "../../../components";
import { ColumnDataType } from "../../../types";

const STATUS_COLORS: Record<PushDeliveryStatus, string> = {
  pending: "blue",
  sent: "teal",
  failed: "red",
  skipped_topic_disabled: "gray",
  skipped_template_disabled: "gray",
  skipped_condition: "gray",
  no_recipients: "yellow",
};

type ComponentProps = {
  t: TFunction;
  deliveries: PushDeliveryItem[];
  refreshKey: number;
  topicName: (key: string) => string;
};

export const PushDeliveriesTab: FC<ComponentProps> = ({ t, deliveries, refreshKey, topicName }) => {
  const dispatch = useAppDispatch();

  const fetchDeliveries = useCallback(() => {
    dispatch(fetchPushDeliveries());
  }, [dispatch]);

  return (
    <>
      <Text size="sm" c="dimmed" px="sm" pt="sm">{t("deliveries.hint")}</Text>
      <DataTable<PushDeliveryItem>
        data={deliveries}
        fetchAction={fetchDeliveries}
        refreshKey={refreshKey}
        useFilters={false}
        usePagination={false}
        columns={[
          {
            id: "createdAt",
            header: t("deliveries.createdAt"),
            accessorKey: "createdAt",
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.DateTime,
            },
          },
          {
            id: "topic",
            header: t("deliveries.topic"),
            accessorKey: "topic",
            enableSorting: true,
            cell: ({ row }) => (
              <Stack gap={0}>
                <Text size="sm" fw={600}>{topicName(row.original.topic)}</Text>
                <Text size="xs" c="dimmed">
                  {Object.entries(row.original.summary).map(([key, value]) => `${key}: ${value}`).join(" · ")}
                </Text>
              </Stack>
            ),
          },
          {
            id: "status",
            header: t("deliveries.status"),
            accessorKey: "status",
            enableSorting: true,
            cell: ({ row }) => {
              const badge = (
                <Badge color={STATUS_COLORS[row.original.status]} variant="light">
                  {t(`deliveries.statuses.${row.original.status}`)}
                </Badge>
              );
              return row.original.error
                ? <Tooltip label={row.original.error} multiline w={320}>{badge}</Tooltip>
                : badge;
            },
          },
          {
            id: "recipients",
            header: t("deliveries.recipients"),
            accessorKey: "recipients",
            enableSorting: true,
            cell: ({ row }) => (
              <Group gap={4}>
                <Text size="sm">{row.original.recipients}</Text>
                {Object.entries(row.original.recipientsByLanguage).map(([lang, count]) => (
                  <Badge key={lang} size="xs" variant="light" color="gray">{lang}: {count}</Badge>
                ))}
              </Group>
            ),
          },
          {
            id: "result",
            header: t("deliveries.result"),
            cell: ({ row }) => (
              <Text size="sm">
                {t("deliveries.resultValue", {
                  success: row.original.successCount,
                  failure: row.original.failureCount,
                  removed: row.original.invalidRemoved,
                })}
              </Text>
            ),
          },
          {
            id: "dedupKey",
            header: t("deliveries.dedupKey"),
            accessorKey: "dedupKey",
            cell: ({ row }) => <Text size="xs" ff="monospace" c="dimmed">{row.original.dedupKey}</Text>,
          },
        ]}
        tableKey="pushDeliveries"
      />
    </>
  );
};
