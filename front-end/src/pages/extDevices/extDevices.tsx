import { FC, useCallback, useEffect } from "react"
import { ExtDeviceItem } from "../../stores/types";
import { connect } from "react-redux";
import { RootState, useAppDispatch } from "../../stores/store";
import { fetchExtDevices } from "../../stores/thunks";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType, LookupSchema } from "../../types";
import { usePageTranslation } from "../../utils";
import { Badge, Group, Text, Tooltip } from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { useLookup, useRefreshKey } from "../../hooks";
import { ObjectId } from "../../schemas";

type ComponentProps = {
  extDevices: ExtDeviceItem[];
  loading: boolean;
  error: string | null;
};

const mapStateToProps = (state: RootState): ComponentProps => ({
  extDevices: state.extDevices.items,
  loading: state.extDevices.loading,
  error: state.extDevices.error,
});

const Component: FC<ComponentProps> = ({ extDevices, loading, error }) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation('devices');
  const { refreshKey } = useRefreshKey();

  const fetchData = useCallback(
    () => {
      dispatch(fetchExtDevices())
    },
    [dispatch],
  );

  const { loading: lookupLoading, data: userLookup } = useLookup(LookupSchema.ReporterUser);

  const getUserName = useCallback((userId: ObjectId | null) => {
    if (!userId) return "";
    const user = userLookup.find(u => u.value === userId);
    return user ? user.text : String(userId);
  }, [userLookup]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <Page loading={loading || lookupLoading}>
      <DataTable<ExtDeviceItem>
        data={extDevices}
        fetchAction={fetchData}
        refreshKey={refreshKey}
        useFilters={false}
        usePagination={false}
        columns={[
          {
            id: 'macAddress',
            header: t('table.macAddress'),
            accessorKey: 'macAddress',
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.Text,
            },
          },
          {
            id: 'fwVersion',
            header: t('table.fwVersion'),
            accessorKey: 'fwVersion',
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.Text,
            },
          },
          {
            id: 'fsVersion',
            header: t('table.fsVersion'),
            accessorKey: 'fsVersion',
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.Text,
            },
          },
          {
            id: 'uptime',
            header: t('table.uptime'),
            accessorKey: 'uptime',
            enableSorting: true,
            cell: ({ row }) => {
              const uptime = row.original.uptime;
              const hours = Math.floor(uptime / 3600);
              const minutes = Math.floor((uptime % 3600) / 60);
              const seconds = uptime % 60;
              return <Text size="sm">{hours}h {minutes}m {seconds}s</Text>
            },
            meta: {
              dataType: ColumnDataType.Number,
            },
          },
          {
            id: 'updatedAt',
            header: t('table.updatedAt'),
            accessorKey: 'updatedAt',
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.DateTime,
            },
          },
          {
            id: 'userId',
            header: t('table.user'),
            accessorKey: 'userId',
            enableSorting: true,
            cell: ({ row }) => <Text size="sm">{getUserName(row.original.userId)}</Text>,
            meta: {
              dataType: ColumnDataType.Id,
            },
          },
          {
            id: 'gridState',
            header: t('table.status'),
            accessorKey: 'gridState',
            enableSorting: true,
            cell: ({ row }) => {
              const gridState = row.original.gridState;
              const isOnline = Date.now()
                - new Date(`${row.original.updatedAt}Z`).getTime() < 120000;
              return (
                <Group gap="xs">
                  <Tooltip label={isOnline ? t('status.online') : t('status.offline')}>
                    <Badge color={isOnline ? "green" : "gray"} variant="dot">
                      {isOnline ? t('status.online') : t('status.offline')}
                    </Badge>
                  </Tooltip>
                  {gridState !== null && (
                    <Tooltip label={gridState ? t('gridState.optionOn') : t('gridState.optionOff')}>
                      <FontAwesomeIcon
                        icon="lightbulb"
                        style={{
                          color: gridState ? '#ffd700' : '#909296',
                          opacity: gridState ? 1 : 0.3,
                        }}
                      />
                    </Tooltip>
                  )}
                </Group>
              );
            },
            meta: {
              dataType: ColumnDataType.Boolean,
              customRender: true,
            },
          },
        ]}
        tableKey="extDevices"
      />
    </Page>
  );
};

export const ExtDevicesPage = connect(mapStateToProps)(Component);
