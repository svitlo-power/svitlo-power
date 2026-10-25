import { FC, useCallback, useEffect, useState } from "react";
import { useAppDispatch, useAppSelector } from "../../stores/store";
import { cancelBotsEditing, fetchBots, saveBots } from "../../stores/thunks";
import {
  cancelCreatingBot,
  createBot,
  startCreatingBot,
  updateBot,
} from "../../stores/slices";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { BotItem } from "../../stores/types";
import { openTokenEditDialog } from "./components/tokenEditDialog";
import { usePageTranslation } from "../../utils";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType } from "../../types";
import { ObjectId } from "../../schemas";
import { selectBotsChanged } from "../../stores/selectors";

export const BotsPage: FC = () => {
  const bots = useAppSelector((state) => state.bots.bots);
  const loading = useAppSelector((state) => state.bots.loading);
  const error = useAppSelector((state) => state.bots.error);
  const changed = useAppSelector(selectBotsChanged);
  const dispatch = useAppDispatch();
  const t = usePageTranslation("bots");
  const [initiallyChanged, setInitiallyChanged] = useState(false);

  const fetchData = useCallback(() => dispatch(fetchBots()), [dispatch]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const create = useCallback(() => {
    dispatch(startCreatingBot());
    openTokenEditDialog({
      create: true,
      token: "",
      t,
      title: t("tokenEdit.set"),
      onClose: (result: boolean, token: string) => {
        if (result) {
          dispatch(createBot(token));
        } else {
          dispatch(cancelCreatingBot());
        }
      },
    });
  }, [dispatch, t]);

  const getHeaderButtons = useCallback(
    (dataChanged: boolean): PageHeaderButton[] => [
      {
        text: t("button.add"),
        icon: "add",
        color: "teal",
        onClick: () => create(),
        disabled: false,
      },
      {
        text: t("button.save"),
        icon: "save",
        color: "green",
        onClick: () => dispatch(saveBots()),
        disabled: !dataChanged,
      },
      {
        text: t("button.cancel"),
        icon: "cancel",
        color: "black",
        onClick: () => dispatch(cancelBotsEditing()),
        disabled: !dataChanged,
      },
    ],
    [create, dispatch, t],
  );

  const { setHeaderButtons, updateButtonAttributes } = useHeaderContent();
  useEffect(() => {
    setHeaderButtons(getHeaderButtons(false));
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons]);

  if (error) {
    return <ErrorMessage content={error} />;
  }

  const onBotHookEnableChange = (id: ObjectId, enabled: boolean) => {
    dispatch(updateBot({ id, hookEnabled: enabled }));
  };
  const onBotEnableChange = (id: ObjectId, enabled: boolean) => {
    dispatch(updateBot({ id, enabled }));
  };

  if (changed != initiallyChanged) {
    setInitiallyChanged(!initiallyChanged);
    setTimeout(() => {
      updateButtonAttributes(1, { disabled: !changed });
      updateButtonAttributes(2, { disabled: !changed });
    }, 1);
  }

  return (
    <Page loading={loading}>
      <DataTable<BotItem>
        data={bots}
        fetchAction={fetchData}
        columns={[
          {
            id: "bot",
            header: t("table.name"),
            enableSorting: true,
            accessorKey: "name",
          },
          {
            id: "canRespondInChat",
            accessorKey: "hookEnabled",
            header: t("table.canRespondInChat"),
            enableSorting: true,
            meta: {
              dataType: ColumnDataType.Boolean,
              readOnly: false,
              checkedChange: (row, state) =>
                onBotHookEnableChange(row.id!, state),
            },
          },
          {
            id: "token",
            header: t("table.token"),
            accessorKey: "token",
          },
          {
            id: "enabled",
            header: t("table.active"),
            enableSorting: true,
            accessorKey: "enabled",
            meta: {
              dataType: ColumnDataType.Boolean,
              readOnly: false,
              checkedChange: (row, state) => onBotEnableChange(row.id!, state),
            },
          },
        ]}
        tableKey={"bots"}
      />
    </Page>
  );
};
