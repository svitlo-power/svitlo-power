import { FC, useCallback, useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../stores/store";
import { fetchMessages, saveMessageStates } from "../../stores/thunks";
import { ServerMessageListItem } from "../../stores/types";
import { useNavigate } from "react-router-dom";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { usePageTranslation } from "../../utils";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType, EventType, LookupSchema } from "../../types";
import { selectMessagesChanged } from "../../stores/selectors";
import { updateMessageState } from "../../stores/slices";
import { modals } from "@mantine/modals";
import { StationsCell } from "./components";
import { useLookup, useSubscribeEvent } from "../../hooks";
import { Row } from "@tanstack/react-table";
import { ObjectId } from "../../schemas";

const Component: FC = () => {
  const messages = useAppSelector((state) => state.messages.messages);
  const dataChanged = useAppSelector(selectMessagesChanged);
  const loading = useAppSelector((state) => state.messages.loading);
  const error = useAppSelector((state) => state.messages.error);
  const [initiallyChanged, setInitiallyChanged] = useState(false);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const t = usePageTranslation("messages");

  const showUnsavedChangesModal = useCallback(
    (confirmAction: () => void) => {
      modals.openConfirmModal({
        title: t("unsaved.title"),
        children: t("unsaved.body"),
        labels: {
          confirm: t("buttons.yes") ?? t("button.confirm"),
          cancel: t("buttons.no") ?? t("button.cancel"),
        },
        confirmProps: { color: "red" },
        onConfirm: confirmAction,
      });
    },
    [t],
  );

  const onCreateClick = useCallback(() => {
    const create = () => navigate(`/messages/create`);
    if (dataChanged) {
      showUnsavedChangesModal(create);
      return;
    }
    create();
  }, [dataChanged, navigate, showUnsavedChangesModal]);

  const onEditClick = (messageId: ObjectId) => {
    const edit = () => navigate(`/messages/edit/${messageId}`);
    if (dataChanged) {
      showUnsavedChangesModal(edit);
    } else {
      navigate(`/messages/edit/${messageId}`);
    }
  };

  const fetchData = useCallback(() => dispatch(fetchMessages()), [dispatch]);

  const getHeaderButtons = useCallback(
    (): PageHeaderButton[] => [
      {
        text: t("button.create") ?? "Create",
        icon: "add",
        color: "teal",
        onClick: () => onCreateClick(),
        disabled: false,
      },
      {
        text: t("button.save") ?? "Save",
        icon: "save",
        color: "green",
        onClick: () => dispatch(saveMessageStates()),
        disabled: !dataChanged,
      },
      {
        text: t("button.cancel") ?? "Cancel",
        icon: "cancel",
        color: "black",
        onClick: fetchData,
        disabled: !dataChanged,
      },
    ],
    [dataChanged, dispatch, fetchData, onCreateClick, t],
  );
  const { setHeaderButtons, updateButtonAttributes } = useHeaderContent();
  useEffect(() => {
    setHeaderButtons(getHeaderButtons());
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const { data: stations } = useLookup(LookupSchema.Station, {
    autoFetch: true,
  });

  if (dataChanged != initiallyChanged) {
    setInitiallyChanged(!initiallyChanged);
    setTimeout(() => {
      updateButtonAttributes(1, { disabled: !dataChanged });
      updateButtonAttributes(2, { disabled: !dataChanged });
    }, 1);
  }

  const onMessageEnableChange = (id: ObjectId, enabled: boolean) => {
    dispatch(updateMessageState({ id, enabled }));
  };

  useSubscribeEvent(EventType.MessagesUpdated, () => {
    fetchData();
  });

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <Page loading={loading}>
      <DataTable<ServerMessageListItem>
        data={messages}
        fetchAction={fetchData}
        columns={[
          {
            id: "name",
            header: t("columns.name"),
            accessorKey: "name",
            enableSorting: true,
          },
          {
            id: "channel",
            header: t("columns.channel"),
            accessorKey: "channelName",
            enableSorting: true,
          },
          {
            id: "stations",
            header: t("columns.stations"),
            accessorKey: "stations",
            enableSorting: true,
            cell: ({ row }) => (
              <StationsCell
                stations={row.original.stations}
                stationsLookup={stations}
              />
            ),
            meta: {
              textAlign: "center",
              dataType: ColumnDataType.Text,
            },
            sortingFn: (
              rowA: Row<ServerMessageListItem>,
              rowB: Row<ServerMessageListItem>,
            ) => {
              const mapToNames = (stationIDs: ObjectId[]) => {
                return stationIDs
                  .map((stationId) =>
                    stations.find((s) => s.value! === stationId),
                  )
                  .join(",");
              };
              const convertedA = mapToNames(rowA.original.stations);
              const convertedB = mapToNames(rowB.original.stations);
              return convertedA.localeCompare(convertedB);
            },
          },
          {
            id: "bot",
            header: t("columns.bot"),
            accessorKey: "botName",
            enableSorting: true,
          },
          {
            id: "lastMessageSent",
            header: t("columns.lastMessageSent"),
            accessorKey: "lastSentTime",
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.DateTime,
            },
          },
          {
            id: "enabled",
            header: t("columns.enabled"),
            accessorKey: "enabled",
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.Boolean,
              readOnly: false,
              checkedChange: (row, state) =>
                onMessageEnableChange(row.id!, state),
            },
          },
          {
            id: "actions",
            meta: {
              dataType: "actions",
              actions: [
                {
                  text: t("actions.edit") ?? "Edit",
                  onlyIcon: true,
                  icon: "edit",
                  color: "teal",
                  clickHandler: (row) => onEditClick(row.id!),
                },
              ],
            },
          },
        ]}
        tableKey={"messages"}
      />
    </Page>
  );
};

export const MessagesPage = Component;
