import { FC, useCallback } from "react";
import { modals } from "@mantine/modals";
import { DataTable, ErrorMessage } from "../components";
import { ColumnDataType } from "../types";
import { useAppDispatch, useAppSelector } from "../stores/store";
import { fetchLoginHistory } from "../stores/thunks";
import { LoginHistoryItem } from "../stores/types";
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

export function openLoginHistoryDialog({
  userId,
  userName,
  t,
}: OpenLoginHistoryDialogOptions) {
  const Inner: FC<{ t: TFunction }> = ({ t }) => {
    const items = useAppSelector((state) => state.loginHistory.items);
    const loading = useAppSelector((state) => state.loginHistory.loading);
    const error = useAppSelector((state) => state.loginHistory.error);
    const dispatch = useAppDispatch();

    const fetchData = useCallback(() => {
      dispatch(fetchLoginHistory({ userId }));
    }, [dispatch]);

    const { refreshKey } = useRefreshKey();

    // if (error) {
    //   return ;
    // }

    // if (loading) {
    //   return <Center py="xl"><Loader /></Center>;
    // }

    return (
      <>
        {error && <ErrorMessage content={error} />}
        {loading && (
          <Center py="xl">
            <Loader />
          </Center>
        )}
        <Stack gap="sm">
          <DataTable<LoginHistoryItem>
            data={items}
            fetchAction={fetchData}
            defSort={[{ id: "loginTime", desc: true }]}
            usePagination={false}
            useFilters={false}
            tableKey={"loginHistory"}
            refreshKey={refreshKey}
            columns={[
              {
                id: "loginTime",
                header: t("table.loginTime"),
                enableSorting: true,
                accessorKey: "loginTime",
                meta: {
                  dataType: ColumnDataType.DateTime,
                },
                cell: ({ row }: { row: { original: LoginHistoryItem } }) => {
                  return toLocalDateTime(row.original.loginTime) || "-";
                },
              },
              {
                id: "ipAddress",
                header: t("table.ipAddress"),
                enableSorting: false,
                accessorKey: "ipAddress",
                meta: {
                  dataType: ColumnDataType.Text,
                },
              },
            ]}
          />
        </Stack>
      </>
    );
  };

  modals.open({
    title: t
      ? t("modal.loginHistoryTitle", { name: userName })
      : `Login history for ${userName}`,
    size: "lg",
    children: <Inner t={t} />,
  });
}
