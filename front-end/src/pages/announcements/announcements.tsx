import { FC, useCallback, useEffect } from "react";
import { connect } from "react-redux";
import { Badge, Stack, Text, Tooltip } from "@mantine/core";
import { modals } from "@mantine/modals";
import { RootState, useAppDispatch } from "../../stores/store";
import { deleteAnnouncement, fetchAnnouncements, publishAnnouncement } from "../../stores/thunks";
import { AnnouncementItem, AnnouncementRequest } from "../../stores/types";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType } from "../../types";
import { usePageTranslation } from "../../utils";
import { useRefreshKey } from "../../hooks";
import i18n from "../../i18n";
import { openAnnouncementDialog } from "./components/announcementDialog";

type ComponentProps = {
  announcements: AnnouncementItem[];
  loading: boolean;
  error: string | null;
};

const mapStateToProps = (state: RootState): ComponentProps => ({
  announcements: state.announcements.items,
  loading: state.announcements.loading,
  error: state.announcements.error,
});

const localized = (value: Record<string, string>) => value[i18n.language] ?? Object.values(value)[0] ?? "";

const Component: FC<ComponentProps> = ({ announcements, loading, error }) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation("announcements");
  const { refreshKey } = useRefreshKey();

  const fetchItems = useCallback(() => {
    dispatch(fetchAnnouncements());
  }, [dispatch]);

  useEffect(() => {
    fetchItems();
  }, [fetchItems]);

  const publish = useCallback(
    (request: AnnouncementRequest) => dispatch(publishAnnouncement(request)).unwrap(),
    [dispatch],
  );

  const handleDelete = useCallback((item: AnnouncementItem) => {
    modals.openConfirmModal({
      title: t("modal.deleteTitle"),
      children: t("modal.deleteConfirm"),
      labels: { confirm: t("button.delete"), cancel: t("button.cancel") },
      confirmProps: { color: "red" },
      onConfirm: () => dispatch(deleteAnnouncement(item.id)),
    });
  }, [dispatch, t]);

  const getHeaderButtons = useCallback((): PageHeaderButton[] => [
    {
      text: t("button.new"),
      icon: "add",
      color: "teal",
      onClick: () => openAnnouncementDialog({ t, onPublish: publish }),
      disabled: false,
    },
  ], [publish, t]);

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
      <Text size="sm" c="dimmed" px="sm" pt="sm">{t("hint")}</Text>
      <DataTable<AnnouncementItem>
        data={announcements}
        fetchAction={fetchItems}
        refreshKey={refreshKey}
        useFilters={false}
        usePagination={false}
        columns={[
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
            id: "title",
            header: t("table.announcement"),
            cell: ({ row }) => (
              <Stack gap={0}>
                <Text size="sm" fw={600}>{localized(row.original.title)}</Text>
                <Text size="xs" c="dimmed" lineClamp={2}>{localized(row.original.body)}</Text>
              </Stack>
            ),
          },
          {
            id: "delivery",
            header: t("table.delivery"),
            cell: ({ row }) => {
              const delivery = row.original.delivery;
              if (!delivery) {
                return <Badge color="blue" variant="light">{t("delivery.pending")}</Badge>;
              }
              return (
                <Tooltip label={delivery.error ?? t("delivery.result", {
                  success: delivery.successCount,
                  failure: delivery.failureCount,
                  recipients: delivery.recipients,
                })}>
                  <Badge color={delivery.status === "sent" ? "teal" : delivery.status === "failed" ? "red" : "gray"}
                    variant="light">
                    {t(`delivery.${delivery.status}`)}
                  </Badge>
                </Tooltip>
              );
            },
          },
          {
            id: "actions",
            meta: {
              dataType: "actions",
              actions: [
                {
                  icon: "trash",
                  color: "red",
                  text: t("button.delete"),
                  onlyIcon: true,
                  clickHandler: (row) => handleDelete(row),
                },
              ],
            },
          },
        ]}
        tableKey="announcements"
      />
    </Page>
  );
};

export const AnnouncementsPage = connect(mapStateToProps)(Component);
