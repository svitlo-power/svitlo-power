import { FC, useCallback } from "react";
import { BuildingCard, BuildingCardProps } from "./buildingCard";
import { Box, Group } from "@mantine/core";
import classes from '../../styles/buildings.module.css';
import { IconButton, OrderControl } from "../../../components";
import { openBuildingEditDialog } from "./buildingEditDialog";
import { useAppDispatch } from "../../../stores/store";
import { modals } from "@mantine/modals";
import { BuildingListItem } from "../../../stores/types";
import { editBuildingOrder } from "../../../stores/thunks";
import { markBuildingForDeletion } from "../../../stores/slices/buildings";
import i18n from "../../../i18n";
import { localizableValueToString } from "../../../utils";

type EditableBuildingCardProps = BuildingCardProps & {
  maxOrder: number;
};

export const EditableBuildingCard: FC<EditableBuildingCardProps> = ({
  t,
  building,
  buildingSummary,
  loadingSummary,
  maxOrder,
}) => {
  const dispatch = useAppDispatch();
  const onDeleteBuilding = useCallback((building: BuildingListItem) => {
    const name = localizableValueToString(building.name);
    modals.openConfirmModal({
      title: t('buildings.delete'),
      children: t('buildings.deletePrompt', { name }),
      labels: { confirm: t('button.confirm'), cancel: t('button.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => dispatch(markBuildingForDeletion(building.id!)),
    });
  }, [dispatch, t]);

  return <Box className={classes.buildingCard}>
    <BuildingCard
      t={t}
      building={building}
      buildingSummary={buildingSummary}
      loadingSummary={loadingSummary}
    />
    <Group justify="space-between" pt='xs' gap='xs' className={classes.buildingCardActions}>
      <OrderControl
        order={building.order}
        maxOrder={maxOrder}
        horizontal={true}
        onOrderChange={(currentOrder, change) => 
          dispatch(editBuildingOrder({ currentOrder, delta: change }))}
      />
      <Group gap='xs'>
        <IconButton
          icon="edit"
          color="blue"
          text={t('buildings.edit')}
          key='btn_edit'
          onClick={() => openBuildingEditDialog({
            creating: false,
            buildingId: building.id!,
            title: `${t('buildings.editDialogTitle', { name: building.name[i18n.language] })}`,
          })}
        />
        <IconButton
          icon="trash"
          color="red"
          text={t('buildings.delete')}
          key='btn_delete'
          onClick={() => onDeleteBuilding(building)}
        />
      </Group>
    </Group>
  </Box>
};
