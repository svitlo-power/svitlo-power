import { FC, useCallback, useEffect, useState } from "react"
import { StationItem } from "../../stores/types";
import { RootState, useAppDispatch } from "../../stores/store";
import { connect } from "react-redux";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { cancelStationsEditing, fetchStations, saveStations } from "../../stores/thunks";
import { createSelector } from "@reduxjs/toolkit";
import { updateStationBatteryCapacity, updateStationOrder, updateStationState } from "../../stores/slices";
import { DataTable, ErrorMessage, OrderControl, Page } from "../../components";
import { ColumnDataType, EventType } from "../../types";
import { ActionIcon, Anchor, Group, Text, Tooltip } from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { openBatteryCapacityEditDialog } from "./components";
import { usePageTranslation } from "../../utils";
import { useNavigate } from "react-router-dom";
import { ObjectId } from "../../schemas";
import { useSubscribeEvent } from "../../hooks";


type ComponentProps = {
  stations: StationItem[];
  maxOrder: number;
  changed: boolean;
  loading: boolean;
  error: string | null;
};

const selectStations = (state: RootState) => state.stations.stations;

const selectChanged = createSelector(
  [selectStations],
  (stations) => stations.some(s => s.changed),
);
const selectMaxOrder = createSelector(
  [selectStations],
  (stations) => Math.max(...stations.map(s => s.order)),
)

const mapStateToProps = (state: RootState): ComponentProps => ({
  stations: state.stations.stations,
  maxOrder: selectMaxOrder(state),
  changed: selectChanged(state),
  loading: state.stations.loading,
  error: state.stations.error,
});

const Component: FC<ComponentProps> = ({ stations, maxOrder, changed, loading, error }: ComponentProps) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation('stations');
  const navigate = useNavigate();
  const [initiallyChanged, setInitiallyChanged] = useState(false);

  const getHeaderButtons = useCallback((dataChanged: boolean): PageHeaderButton[] => [
    { text: t('button.save'), icon: "save", color: "green", onClick: () => dispatch(saveStations()), disabled: !dataChanged, },
    { text: t('button.cancel'), icon: "cancel", color: "black", onClick: () => dispatch(cancelStationsEditing()), disabled: !dataChanged, },
  ], [dispatch, t]);
  const { setHeaderButtons, updateButtonAttributes } = useHeaderContent();
  useEffect(() => {
    setHeaderButtons(getHeaderButtons(changed));
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons, changed]);  

  const fetchData = useCallback(() => dispatch(fetchStations()), [dispatch]);

  useSubscribeEvent(EventType.StationDataUpdated, () => {
    fetchData();
  });

  if (error) {
    return <ErrorMessage content={error} />;
  }

  const onStationEnableChange = (id: ObjectId, enabled: boolean) => {
    dispatch(updateStationState({ id, enabled }));
  };
  const onStationOrderChange = (currentOrder: number, delta: number) => {
    dispatch(updateStationOrder({ currentOrder, delta }));
  };
  const onSetBatteryCapacity = (id: ObjectId, batteryCapacity: number) => {
    dispatch(updateStationBatteryCapacity({ id, batteryCapacity }));
  }

  if (changed != initiallyChanged) {
    setInitiallyChanged(!initiallyChanged);
    setTimeout(() => {
      updateButtonAttributes(0, { disabled: !changed });
      updateButtonAttributes(1, { disabled: !changed });
    }, 1);
  }

  return <Page loading={loading}>
    <DataTable<StationItem>
      data={stations}
      fetchAction={fetchData}
      tableKey="stations"
      useSorting={false}
      columns={[
        {
          id: 'stationName',
          header: t('table.name'),
          accessorKey: "stationName",
          cell: ({ row }) => {
            return (
              <Anchor
                component="button"
                onClick={() => navigate(`/stations/details/${row.original.id}`)}
                fw={500}
              >
                {row.original.stationName}
              </Anchor>
            );
          }
        },
        {
          id: 'connectionStatus',
          header: t('table.connectionStatus'),
          accessorKey: 'connectionStatus',
        },
        {
          id: 'mode',
          header: t('table.mode'),
          accessorKey: 'gridInterconnectionType',
        },
        {
          id: 'lastUpdate',
          header: t('table.lastUpdated'),
          accessorKey: 'lastUpdateTime',
          meta: {  
            dataType: ColumnDataType.DateTime,
          },
        },
        {
          id: 'enabled',
          header: t('table.enabled'),
          accessorKey: 'enabled',
          meta: {
            dataType: ColumnDataType.Boolean,
            textAlign: 'center',
            checkedChange: (row, state) => onStationEnableChange(row.id, state),
          },
        },
        {
          id: 'battery capacity',
          header: t('table.batteryCapacity'),
          accessorKey: 'batteryCapacity',
          meta: {
            dataType: ColumnDataType.Number,
          },
          cell: ({ renderValue, row }) => {
            return <Group justify="space-between">
              <Text>{t('batteryEdit.valueLabel', { value: renderValue() })}</Text>
              <Tooltip
                ml='sm'
                label={
                  <Text fw={500} fz={13}>
                    {t('batteryEdit.tooltip')}
                  </Text>
                }
              >
                <ActionIcon
                  color="teal"
                  onClick={() => openBatteryCapacityEditDialog({
                    batteryCapacity: row.original.batteryCapacity,
                    t,
                    title: t('batteryEdit.title'),
                    onClose: (result, newCapacity) => {
                      if (result) {
                        onSetBatteryCapacity(row.original.id, newCapacity)
                      }
                    }
                  })}
                >
                  <FontAwesomeIcon icon='edit' />
                </ActionIcon>
              </Tooltip>
            </Group>;
          }
        },
        {
          id: 'order',
          header: t('table.order'),
          accessorKey: 'order',
          meta: {
            dataType: ColumnDataType.Number,
            textAlign: 'center',
          },
          cell: ({ row }) => {
            return <OrderControl
              order={row.original.order}
              maxOrder={maxOrder}
              onOrderChange={(currentOrder, change) => {
                onStationOrderChange(currentOrder, change);
              }}
            />;
          },
        }
      ]}
    />
  </Page>
};

export const StationsPage = connect(mapStateToProps)(Component);