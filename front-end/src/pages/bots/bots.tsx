import { FC, useCallback, useEffect, useState } from "react";
import { shallowEqual } from "react-redux";
import { RootState, useAppDispatch, useAppSelector } from "../../stores/store";
import { cancelBotsEditing, fetchBots, saveBots } from "../../stores/thunks";
import {
  cancelCreatingBot,
  createBot,
  startCreatingBot,
  updateBot,
} from "../../stores/slices";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { createSelector } from "@reduxjs/toolkit";
import { BotItem } from "../../stores/types";
import { openTokenEditDialog } from "./components/tokenEditDialog";
import { usePageTranslation } from "../../utils";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType } from "../../types";
import { ObjectId } from "../../schemas";

type ComponentProps = {
  bots: Array<BotItem>;
  loading: boolean;
  error: string | null;
  changed: boolean;
  creating: boolean;
};

const selectBots = (state: RootState) => state.bots.bots;

const selectChanged = createSelector([selectBots], (bots) =>
  bots.some((b) => b.changed),
);

const mapStateToProps = (state: RootState): ComponentProps => ({
  bots: state.bots.bots,
  loading: state.bots.loading,
  error: state.bots.error,
  changed: selectChanged(state),
  creating: state.bots.creating,
});

const Component: FC<ComponentProps> = ({
  bots,
  loading,
  error,
  changed,
}: ComponentProps) => {
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

const ConnectedComponent: FC = () => {
  const props = useAppSelector(mapStateToProps, shallowEqual);
  return <Component {...props} />;
};

export const BotsPage = ConnectedComponent;
