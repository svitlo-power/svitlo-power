import { FC, useCallback, useEffect, useMemo, useState } from "react";
import { ExtDataItem } from "../../stores/types";
import { useAppDispatch, useAppSelector } from "../../stores/store";
import {
  createExtData,
  deleteExtData,
  ExtDataRequest,
  fetchExtData,
} from "../../stores/thunks";
import { DataTable, ErrorMessage, Page } from "../../components";
import {
  ColumnDataType,
  EventType,
  FilterConfig,
  LookupSchema,
  PagingConfig,
  SortingConfig,
} from "../../types";
import { usePageTranslation } from "../../utils";
import { Column } from "@tanstack/react-table";
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Switch,
  Text,
  Tooltip,
} from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { modals } from "@mantine/modals";
import { DateTimePicker } from "@mantine/dates";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { useLookup, useRefreshKey, useSubscribeEvent } from "../../hooks";
import { ObjectId } from "../../schemas";

const Component: FC = () => {
  const extData = useAppSelector((state) => state.extData.items);
  const pagingInfo = useAppSelector((state) => state.extData.paging);
  const loading = useAppSelector((state) => state.extData.loading);
  const error = useAppSelector((state) => state.extData.error);
  const dispatch = useAppDispatch();
  const t = usePageTranslation("extData");
  const [modalOpened, setModalOpened] = useState(false);
  const [formData, setFormData] = useState({
    user_id: null as ObjectId | null,
    grid_state: false,
    received_at: null as Date | string | null,
  });

  const fetchData = useCallback(
    (
      paging?: PagingConfig,
      sorting?: SortingConfig,
      filters?: FilterConfig[],
    ) => {
      const request: ExtDataRequest = {
        paging: paging!,
        sorting: sorting!,
        filters: filters!,
      };
      dispatch(fetchExtData(request));
    },
    [dispatch],
  );

  const { loading: lookupLoading, data: userLookup } = useLookup(
    LookupSchema.ReporterUser,
  );

  const userLookupOptions = useMemo(() => {
    return userLookup.map((user) => ({
      value: String(user.value),
      label: user.text,
    }));
  }, [userLookup]);

  const UserFilter = (column: Column<ExtDataItem, unknown>) => {
    const value = column.getFilterValue() as string | undefined;

    return (
      <Select
        placeholder={t("filters.allUsers")}
        data={userLookupOptions}
        value={value || null}
        onChange={(val) => column.setFilterValue(val || undefined)}
        clearable
        searchable
      />
    );
  };

  const GridStateFilter = (column: Column<ExtDataItem, unknown>) => {
    const value = column.getFilterValue() as string | undefined;

    return (
      <Select
        placeholder={t("filters.all")}
        data={[
          { value: "true", label: t("gridState.optionOn") },
          { value: "false", label: t("gridState.optionOff") },
        ]}
        value={value || null}
        onChange={(val) => column.setFilterValue(val || undefined)}
        clearable
      />
    );
  };

  const handleOpenCreateModal = useCallback(() => {
    setFormData({
      user_id: null,
      grid_state: false,
      received_at: null,
    });
    setModalOpened(true);
  }, []);

  const handleCloseModal = useCallback(() => {
    setModalOpened(false);
  }, []);

  const { refreshKey, refresh } = useRefreshKey();

  const handleCreate = useCallback(() => {
    if (!formData.user_id) return;

    const data: {
      user_id: ObjectId;
      grid_state: boolean;
      received_at?: string;
    } = {
      user_id: formData.user_id,
      grid_state: formData.grid_state,
    };

    if (formData.received_at) {
      if (formData.received_at instanceof Date) {
        data.received_at = formData.received_at.toISOString();
      } else {
        const date = new Date(formData.received_at);
        if (!isNaN(date.getTime())) {
          data.received_at = date.toISOString();
        }
      }
    }

    dispatch(createExtData(data))
      .unwrap()
      .then(() => {
        handleCloseModal();
      })
      .catch((err) => {
        console.error("Failed to create ext data:", err);
      });
  }, [
    formData.user_id,
    formData.grid_state,
    formData.received_at,
    dispatch,
    handleCloseModal,
  ]);

  const getUserName = useCallback(
    (userId?: ObjectId): string => {
      return userLookup?.find((f) => f.value === userId)?.text ?? "unknown";
    },
    [userLookup],
  );

  const handleDelete = useCallback(
    (item: ExtDataItem) => {
      if (!item.id) {
        return;
      }
      modals.openConfirmModal({
        title: t("modal.deleteConfirmTitle"),
        children: t("modal.deleteConfirmMessage", {
          user: getUserName(item.userId),
          state: item.gridState ? t("gridState.on") : t("gridState.off"),
        }),
        labels: {
          confirm: t("button.delete") ?? "Delete",
          cancel: t("button.cancel") ?? "Cancel",
        },
        confirmProps: { color: "red" },
        onConfirm: () => {
          dispatch(deleteExtData(item.id!))
            .unwrap()
            .then(() => refresh())
            .catch((err) => {
              console.error("Failed to delete ext data:", err);
            });
        },
      });
    },
    [dispatch, getUserName, refresh, t],
  );

  const getHeaderButtons = useCallback(
    (): PageHeaderButton[] => [
      {
        text: t("button.createEvent"),
        icon: "add",
        color: "teal",
        onClick: handleOpenCreateModal,
        disabled: false,
      },
    ],
    [handleOpenCreateModal, t],
  );

  const { setHeaderButtons } = useHeaderContent();

  useEffect(() => {
    setHeaderButtons(getHeaderButtons());
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons]);

  useSubscribeEvent(EventType.ExtDataUpdated, () => {
    refresh();
  });

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <>
      <Page loading={loading}>
        <DataTable<ExtDataItem>
          data={extData}
          fetchAction={fetchData}
          refreshKey={refreshKey}
          defSort={[{ id: "received_at", desc: true }]}
          useFilters={true}
          usePagination={true}
          manualPagination={true}
          manualFiltering={true}
          manualSorting={true}
          pagingInfo={pagingInfo}
          columns={[
            {
              id: "user_id",
              header: t("table.user"),
              accessorKey: "userId",
              enableSorting: true,
              enableColumnFilter: true,
              meta: {
                dataType: ColumnDataType.Id,
                filterOptions: {
                  customFilterCell: UserFilter,
                },
              },
              cell: ({ row }) => {
                return <Text>{getUserName(row.original.userId)}</Text>;
              },
            },
            {
              id: "grid_state",
              header: t("table.gridState"),
              accessorKey: "gridState",
              enableColumnFilter: true,
              enableSorting: true,
              meta: {
                customRender: true,
                dataType: ColumnDataType.Boolean,
                filterOptions: {
                  customFilterCell: GridStateFilter,
                },
              },
              cell: ({ row }) => {
                const gridState = row.original.gridState;
                return (
                  <Group justify="center">
                    <Tooltip
                      label={
                        gridState
                          ? t("gridState.tooltipOn")
                          : t("gridState.tooltipOff")
                      }
                    >
                      <FontAwesomeIcon
                        icon="lightbulb"
                        size="lg"
                        style={{
                          color: gridState ? "#ffd700" : "#909296",
                          opacity: gridState ? 1 : 0.3,
                        }}
                      />
                    </Tooltip>
                  </Group>
                );
              },
            },
            {
              id: "received_at",
              header: t("table.receivedAt"),
              accessorKey: "receivedAt",
              enableSorting: true,
              enableColumnFilter: true,
              meta: {
                dataType: ColumnDataType.DateTime,
                filterOptions: {},
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
          tableKey="extData"
        />
      </Page>

      <Modal
        opened={modalOpened}
        onClose={handleCloseModal}
        title={t("modal.createTitle")}
      >
        <Stack>
          <Select
            label={t("modal.userLabel")}
            placeholder={t("modal.selectUserPlaceholder")}
            data={userLookupOptions}
            value={formData.user_id ? String(formData.user_id) : null}
            onChange={(val) => setFormData({ ...formData, user_id: val })}
            searchable
            required
            disabled={lookupLoading}
          />
          <Switch
            label={t("modal.gridStateLabel")}
            checked={formData.grid_state}
            onChange={(e) =>
              setFormData({ ...formData, grid_state: e.currentTarget.checked })
            }
            onLabel={<FontAwesomeIcon icon="lightbulb" />}
            offLabel={<FontAwesomeIcon icon="lightbulb" />}
          />
          <DateTimePicker
            label={t("modal.receivedAtLabel")}
            placeholder={t("modal.selectReceivedAtPlaceholder")}
            value={formData.received_at}
            onChange={(val) => setFormData({ ...formData, received_at: val })}
            clearable
            highlightToday
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={handleCloseModal}>
              {t("button.cancel")}
            </Button>
            <Button onClick={handleCreate} disabled={!formData.user_id}>
              {t("button.create")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </>
  );
};

export const ExtDataPage = Component;
