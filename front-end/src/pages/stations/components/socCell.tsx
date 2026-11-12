import { FC } from "react";
import { ActionIcon, Group, Stack, Text, Tooltip } from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { openSocEditDialog } from "./socEditDialog";
import { ObjectId } from "../../../schemas";
import { TFunction } from "i18next";

type SocCellProps = {
  t: TFunction;
  id: ObjectId;
  dischargeTargetSoc: number | null;
  chargeTargetSoc: number | null;
  defaultDischargeTargetSoc: number;
  defaultChargeTargetSoc: number;
  onSocChange: (
    id: ObjectId,
    dischargeTargetSoc: number | null,
    chargeTargetSoc: number | null
  ) => void;
}

export const SocCell: FC<SocCellProps> = ({ t, id, dischargeTargetSoc, chargeTargetSoc, defaultDischargeTargetSoc, defaultChargeTargetSoc, onSocChange }) => {
  const dischargeValue = dischargeTargetSoc && !isNaN(dischargeTargetSoc!) ? dischargeTargetSoc : defaultDischargeTargetSoc ?? 0;
  const chargeValue = chargeTargetSoc && !isNaN(chargeTargetSoc!) ? chargeTargetSoc : defaultChargeTargetSoc ?? 0;
  const dischargeFromSetting = dischargeTargetSoc === null || isNaN(dischargeTargetSoc);
  const chargeFromSetting = chargeTargetSoc === null || isNaN(chargeTargetSoc);

  return <Group justify="space-between">
    <Stack gap={0}>
      <Text size="sm" c={dischargeFromSetting ? "dimmed" : undefined}>
        {t("socEdit.dischargeShort")}: {dischargeValue}%
      </Text>
      <Text size="sm" c={chargeFromSetting ? "dimmed" : undefined}>
        {t("socEdit.chargeShort")}: {chargeValue}%
      </Text>
    </Stack>
    <Tooltip
      ml='sm'
      label={
        <Text fw={500} fz={13}>
          {t('socEdit.tooltip')}
        </Text>
      }
    >
      <ActionIcon
        color="teal"
        onClick={() => openSocEditDialog({
          dischargeTargetSoc,
          chargeTargetSoc,
          defaultDischargeTargetSoc,
          defaultChargeTargetSoc,
          t,
          title: t('socEdit.title'),
          onClose: (result, newDischarge, newCharge) => {
            if (result) {
              onSocChange(id, newDischarge, newCharge)
            }
          }
        })}
      >
        <FontAwesomeIcon icon='edit' />
      </ActionIcon>
    </Tooltip>
  </Group>;
};
