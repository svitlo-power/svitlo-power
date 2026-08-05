import { FC } from "react";
import { LocalizableValue, ObjectId } from "../../../schemas";
import { ActionIcon, Group, Stack, Text, Tooltip } from "@mantine/core";
import { AVAILABLE_LANGUAGES } from "../../../i18n";
import { CountryFlag } from "../../../components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { openAliasEditDialog } from "./aliasEditDialog";
import { TFunction } from "i18next";

type AliasCellProps = {
  t: TFunction;
  id: ObjectId;
  name: string;
  value: LocalizableValue;
  onAliasChange: (id: ObjectId, newAlias: LocalizableValue) => void;
};

export const AliasCell: FC<AliasCellProps> = ({ t, id, name, value, onAliasChange }) => {
  return <Group justify="space-between">
    <Stack gap={0}>
      {AVAILABLE_LANGUAGES.map(lang => {
        return <Group gap={'xs'} key={lang}>
          <CountryFlag language={lang} />
          <Text>{value?.[lang] ?? name}</Text>
        </Group>;
      })}
    </Stack>
    <Tooltip
      ml='sm'
      label={
        <Text fw={500} fz={13}>
          {t('aliasEdit.tooltip')}
        </Text>
      }
    >
      <ActionIcon
        color="teal"
        onClick={() => openAliasEditDialog({
          alias: value ?? { en: name, uk: name },
          t,
          title: t('aliasEdit.title'),
          onClose: (result, newAlias) => {
            if (result) {
              onAliasChange(id, newAlias)
            }
          }
        })}
      >
        <FontAwesomeIcon icon='edit' />
      </ActionIcon>
    </Tooltip>
  </Group>
};