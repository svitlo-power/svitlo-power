import { FC, useCallback } from "react";
import { modals } from "@mantine/modals";
import { DataTable, ErrorMessage } from "../components";
import { ColumnDataType } from "../types";
import { RootState, useAppDispatch } from "../stores/store";
import { fetchLoginHistory } from "../stores/thunks";
import { LoginHistoryItem } from "../stores/types";
import { connect } from "react-redux";
import { ObjectId } from "../schemas";
import { TFunction } from "i18next";
import { toLocalDateTime } from "../utils";
import { Center, Loader, Stack } from "@mantine/core";
import { useRefreshKey } from "../hooks";

type OpenLoginHistoryDialogOptions = {
  userId: ObjectId;
  userName: string;
  t: TFunction;
};

export function openLoginHistoryDialog({ userId, userName, t }: OpenLoginHistoryDialogOptions) {

  type InnerProps = {
    items: LoginHistoryItem[];
    loading: boolean;
    error: string | null;
    t: TFunction;
  };

  const selectLoginHistory = (state: RootState) => state.loginHistory;

  const mapStateToProps = (state: RootState, ownProps: { t: TFunction }): InnerProps => ({
    items: selectLoginHistory(state).items,
    loading: selectLoginHistory(state).loading,
    error: selectLoginHistory(state).error,
    t: ownProps.t,
  });

  const Inner: FC<InnerProps> = ({ items, loading, error, t }) => {
    const dispatch = useAppDispatch();

    const fetchData = useCallback(
      () => {
        dispatch(fetchLoginHistory({ userId }))
      },
      [dispatch],
    );

    const { refreshKey } = useRefreshKey();

    // if (error) {
    //   return ;
    // }

    // if (loading) {
    //   return <Center py="xl"><Loader /></Center>;
    // }

    return <>
      { error && <ErrorMessage content={error} /> }
      { loading && <Center py="xl"><Loader /></Center> }
      <Stack gap="sm">
        <DataTable<LoginHistoryItem>
          data={items}
          fetchAction={fetchData}
          defSort={[{ id: 'loginTime', desc: true }]}
          usePagination={false}
          useFilters={false}
          tableKey={"loginHistory"}
          refreshKey={refreshKey}
          columns={[
            {
              id: 'loginTime',
              header: t('table.loginTime'),
              enableSorting: true,
              accessorKey: 'loginTime',
              meta: {
                dataType: ColumnDataType.DateTime,
              },
              cell: ({ row }: { row: { original: LoginHistoryItem } }) => {
                return toLocalDateTime(row.original.loginTime) || '-';
              },
            },
            {
              id: 'ipAddress',
              header: t('table.ipAddress'),
              enableSorting: false,
              accessorKey: 'ipAddress',
              meta: {
                dataType: ColumnDataType.Text,
              },
            },
          ]}
        />
      </Stack>
    </>;
  };

  const ConnectedInner = connect(mapStateToProps)(Inner);

  modals.open({
    title: t ? t('modal.loginHistoryTitle', { name: userName }) : `Login history for ${userName}`,
    size: 'lg',
    children: <ConnectedInner t={t} />,
  });
}
