import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Group, ActionIcon, Text, Tooltip } from "@mantine/core";
import { TFunction } from "i18next";
import { FC } from "react";
import { openBatteryCapacityEditDialog } from "./batteryCapacityEditDialog";
import { ObjectId } from "../../../schemas";

type BatteryCapacityCellProps = {
  t: TFunction;
  id: ObjectId;
  value: number;
  onBatteryCapacityChange: (id: ObjectId, newBatteryCapacity: number) => void;
}

export const BatteryCapacityCell: FC<BatteryCapacityCellProps> = ({ t, id, value, onBatteryCapacityChange }) => {
  return <Group justify="space-between">
      <Text>{t('batteryEdit.valueLabel', { value })}</Text>
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
            batteryCapacity: value,
            t,
            title: t('batteryEdit.title'),
            onClose: (result, newCapacity) => {
              if (result) {
                onBatteryCapacityChange(id, newCapacity)
              }
            }
          })}
        >
          <FontAwesomeIcon icon='edit' />
        </ActionIcon>
      </Tooltip>
    </Group>;
};