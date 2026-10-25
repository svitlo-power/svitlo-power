import { FC, useCallback, useEffect } from "react";
import { AllowedChatListItem, ChatRequestListItem } from "../../stores/types";
import { shallowEqual } from "react-redux";
import { RootState, useAppDispatch, useAppSelector } from "../../stores/store";
import {
  approveChatRequest,
  disallowChat,
  fetchAllowedChats,
  fetchChatRequests,
  rejectChatRequest,
} from "../../stores/thunks";
import { DataTable, ErrorMessage, Page } from "../../components";
import { Title } from "@mantine/core";
import { usePageTranslation } from "../../utils";
import { ColumnDataType, EventType } from "../../types";
import { ObjectId } from "../../schemas";
import { useSubscribeEvent } from "../../hooks";

type ComponentProps = {
  allowedChats: AllowedChatListItem[];
  chatRequests: ChatRequestListItem[];
  loading: boolean;
  error: string | null;
};

const mapStateToProps = (state: RootState): ComponentProps => ({
  allowedChats: state.chats.allowedChats,
  chatRequests: state.chats.chatRequests,
  loading: state.chats.loading,
  error: state.chats.error,
});

const Component: FC<ComponentProps> = ({
  allowedChats,
  chatRequests,
  loading,
  error,
}) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation("chats");

  const fetchChats = useCallback(
    () => dispatch(fetchAllowedChats()),
    [dispatch],
  );
  const fetchRequests = useCallback(
    () => dispatch(fetchChatRequests()),
    [dispatch],
  );

  useEffect(() => {
    fetchChats();
    fetchRequests();
  }, [dispatch, fetchChats, fetchRequests]);

  const approveClick = (id: ObjectId) => {
    dispatch(approveChatRequest(id));
  };

  const rejectClick = (id: ObjectId) => {
    dispatch(rejectChatRequest(id));
  };

  const disallowClick = (id: ObjectId) => {
    dispatch(disallowChat(id));
  };

  useSubscribeEvent(EventType.ChatsUpdated, () => {
    fetchChats();
    fetchRequests();
  });

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <>
      <Page loading={loading}>
        <Title mt="sm" ta="center" order={4}>
          {t("allowed.title")}
        </Title>
        <DataTable<AllowedChatListItem>
          data={allowedChats}
          fetchAction={fetchChats}
          columns={[
            {
              id: "chat",
              header: t("table.chat"),
              accessorKey: "chatName",
              enableSorting: true,
            },
            {
              id: "bot",
              header: t("table.bot"),
              accessorKey: "botName",
              enableSorting: true,
            },
            {
              id: "approveDate",
              header: t("table.approvedOn"),
              accessorKey: "approveDate",
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
                    text: t("actions.disallow"),
                    icon: "cancel",
                    color: "red",
                    clickHandler: (row) => disallowClick(row.id!),
                  },
                ],
              },
            },
          ]}
          tableKey="allowedChats"
        />
      </Page>
      <Page loading={loading} mt="sm">
        <Title mt="sm" ta="center" order={4}>
          {t("requests.title")}
        </Title>
        <DataTable<ChatRequestListItem>
          data={chatRequests}
          fetchAction={fetchRequests}
          columns={[
            {
              id: "chat",
              header: t("table.chat"),
              accessorKey: "chatName",
              enableSorting: true,
            },
            {
              id: "bot",
              header: t("table.bot"),
              accessorKey: "botName",
              enableSorting: true,
            },
            {
              id: "requestDate",
              header: t("table.requestedOn"),
              accessorKey: "requestDate",
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
                    text: t("actions.approve"),
                    icon: "check",
                    color: "green",
                    clickHandler: (row) => approveClick(row.id!),
                  },
                  {
                    text: t("actions.reject"),
                    icon: "cancel",
                    color: "red",
                    clickHandler: (row) => rejectClick(row.id!),
                  },
                ],
              },
            },
          ]}
          tableKey="chatRequests"
        />
      </Page>
    </>
  );
};

const ConnectedComponent: FC = () => {
  const props = useAppSelector(mapStateToProps, shallowEqual);
  return <Component {...props} />;
};

export const ChatsPage = ConnectedComponent;
