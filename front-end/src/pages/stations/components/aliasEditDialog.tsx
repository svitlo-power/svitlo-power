import { Button, Divider, Group } from "@mantine/core";
import { modals } from "@mantine/modals";
import { FC, useState } from "react";
import { TFunction } from "i18next";
import { LocalizableValue } from "../../../schemas";
import { LocalizableValueEditor } from "../../../components";

type AliasEditOptions = {
  alias: LocalizableValue;
  onClose: (result: boolean, alias: LocalizableValue) => void;
  title?: string;
  t: TFunction;
};

export function openAliasEditDialog({
  alias,
  onClose,
  title,
  t,
}: AliasEditOptions) {
  const Inner: FC = () => {
    const [editingAlias, setAlias] = useState<LocalizableValue>(alias);

    const handleSave = () => {
      if (id) {
        modals.close(id);
      }
      onClose(true, editingAlias);
    };

    const handleCancel = () => {
      if (id) {
        modals.close(id);
      }
      onClose(false, alias);
    };
    return <>
      <LocalizableValueEditor
        t={t}
        label={t('aliasEdit.label')}
        data-autofocus
        value={editingAlias}
        onChange={(e) => setAlias(e)}
      />
      <Divider mt='sm' mb='sm' />
      <Group gap={'sm'} justify='flex-end'>
        <Button variant="default" onClick={handleCancel}>
          {t('button.cancel')}
        </Button>
        <Button onClick={handleSave}>{t('button.save')}</Button>
      </Group>
    </>;
  };

  const id: string | undefined = modals.open({
    title: title ?? (t('aliasEdit.title')),
    centered: true,
    children: <Inner />,
  });
}
