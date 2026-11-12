import { Button, Divider, Group, NumberInput, Stack } from "@mantine/core";
import { modals } from "@mantine/modals";
import { FC, useState } from "react";
import { TFunction } from "i18next";

type SocEditOptions = {
  dischargeTargetSoc: number | null;
  chargeTargetSoc: number | null;
  defaultDischargeTargetSoc: number | null;
  defaultChargeTargetSoc: number | null;
  onClose: (
    result: boolean,
    dischargeTargetSoc: number | null,
    chargeTargetSoc: number | null
  ) => void;
  title?: string;
  t: TFunction;
};

export function openSocEditDialog({
  dischargeTargetSoc,
  chargeTargetSoc,
  defaultDischargeTargetSoc,
  defaultChargeTargetSoc,
  onClose,
  title,
  t,
}: SocEditOptions) {
  const Inner: FC = () => {
    const [editingDischarge, setDischarge] = useState<number | null>(
      dischargeTargetSoc
    );
    const [editingCharge, setCharge] = useState<number | null>(
      chargeTargetSoc
    );

    const getSocValue = (e: number | string) => {
      return e === null || e.toString().trim() === '' ? null : parseInt(e.toString());
    };

    const handleSave = () => {
      if (id) {
        modals.close(id);
      }
      onClose(true, editingDischarge, editingCharge);
    };

    const handleCancel = () => {
      if (id) {
        modals.close(id);
      }
      onClose(false, dischargeTargetSoc, chargeTargetSoc);
    };

    const dischargeFromSetting = editingDischarge === null;
    const chargeFromSetting = editingCharge === null;

    return (
      <Stack gap="sm">
        <NumberInput
          label={t("socEdit.dischargeLabel")}
          data-autofocus
          value={editingDischarge!}
          onChange={(e) => setDischarge(getSocValue(e))}
          min={0}
          max={100}
          step={1}
          style={dischargeFromSetting ? { opacity: 0.5 } : undefined}
          placeholder={
            dischargeFromSetting
              ? t("socEdit.useSetting", { value: defaultDischargeTargetSoc ?? 0 })
              : ""
          }
        />
        <NumberInput
          label={t("socEdit.chargeLabel")}
          value={editingCharge!}
          onChange={(e) => setCharge(getSocValue(e))}
          min={0}
          max={100}
          step={1}
          style={chargeFromSetting ? { opacity: 0.5 } : undefined}
          placeholder={
            chargeFromSetting
              ? t("socEdit.useSetting", { value: defaultChargeTargetSoc ?? 0 })
              : ""
          }
        />
        <Divider mt='sm' mb='sm' />
        <Group gap={'sm'} justify='flex-end'>
          <Button variant="default" onClick={handleCancel}>
            {t('button.cancel')}
          </Button>
          <Button onClick={handleSave}>{t('button.save')}</Button>
        </Group>
      </Stack>
    );
  };

  const id: string | undefined = modals.open({
    title: title ?? t("socEdit.title"),
    centered: true,
    children: <Inner />,
  });
}
