import { FC, useEffect, useState } from "react";
import { TFunction } from "i18next";
import { modals } from "@mantine/modals";
import { Button, Checkbox, Group, PasswordInput, Stack, TextInput } from "@mantine/core";
import { useAppDispatch } from "../../../stores/store";
import { StationConnectionEditItem, ServerStationConnectionItem } from "../../../stores/types";
import { createStationConnection, saveStationConnection } from "../../../stores/thunks";
import apiClient from "../../../utils/apiClient";

type OpenConnectionEditOptions = {
  create?: boolean;
  connection?: ServerStationConnectionItem;
  t: TFunction;
};

type ConnectionDefaults = {
  baseUrl: string | null;
};

export function openConnectionEditDialog({ create = false, connection, t }: OpenConnectionEditOptions) {
  const Inner: FC = () => {
    const dispatch = useAppDispatch();
    // Secrets are never prefilled - empty values mean "keep the stored ones" on edit
    const [form, setForm] = useState<StationConnectionEditItem>({
      name: connection?.name ?? '',
      baseUrl: connection?.baseUrl ?? '',
      appId: connection?.appId ?? '',
      appSecret: '',
      email: connection?.email ?? '',
      password: '',
      syncStationsOnPoll: connection?.syncStationsOnPoll ?? false,
    });

    useEffect(() => {
      if (!create) {
        return;
      }
      apiClient.get<ConnectionDefaults>('/station-connections/defaults')
        .then(({ data }) => {
          if (data.baseUrl) {
            setForm(f => f.baseUrl ? f : { ...f, baseUrl: data.baseUrl! });
          }
        })
        .catch(() => {});
    }, []);

    const setField = <K extends keyof StationConnectionEditItem>(field: K, value: StationConnectionEditItem[K]) => {
      setForm(f => ({ ...f, [field]: value }));
    };

    const isValid =
      form.name.trim() !== '' &&
      form.baseUrl.trim() !== '' &&
      form.appId.trim() !== '' &&
      form.email.trim() !== '' &&
      (!create || (form.appSecret !== '' && form.password !== ''));

    const handleSave = () => {
      if (create) {
        dispatch(createStationConnection(form));
      } else {
        dispatch(saveStationConnection({ id: connection!.id, connection: form }));
      }
      if (id) {
        modals.close(id);
      }
    };

    const handleCancel = () => {
      if (id) {
        modals.close(id);
      }
    };

    const secretPlaceholder = create ? undefined : t('connections.fields.secretPlaceholder');

    return (
      <Stack>
        <TextInput
          required
          label={t('connections.fields.name')}
          value={form.name}
          onChange={(e) => setField('name', e.currentTarget.value)}
        />
        <TextInput
          required
          label={t('connections.fields.baseUrl')}
          value={form.baseUrl}
          onChange={(e) => setField('baseUrl', e.currentTarget.value)}
        />
        <TextInput
          required
          label={t('connections.fields.appId')}
          value={form.appId}
          onChange={(e) => setField('appId', e.currentTarget.value)}
        />
        <PasswordInput
          required={create}
          label={t('connections.fields.appSecret')}
          placeholder={secretPlaceholder}
          value={form.appSecret}
          onChange={(e) => setField('appSecret', e.currentTarget.value)}
        />
        <TextInput
          required
          label={t('connections.fields.email')}
          value={form.email}
          onChange={(e) => setField('email', e.currentTarget.value)}
        />
        <PasswordInput
          required={create}
          label={t('connections.fields.password')}
          placeholder={secretPlaceholder}
          value={form.password}
          onChange={(e) => setField('password', e.currentTarget.value)}
        />
        <Checkbox
          label={t('connections.fields.syncStationsOnPoll')}
          checked={form.syncStationsOnPoll}
          onChange={(e) => setField('syncStationsOnPoll', e.currentTarget.checked)}
        />
        <Group justify="flex-end">
          <Button onClick={handleSave} disabled={!isValid}>
            {t('button.save')}
          </Button>
          <Button variant="default" onClick={handleCancel}>
            {t('button.cancel')}
          </Button>
        </Group>
      </Stack>
    );
  };

  const id: string | undefined = modals.open({
    title: create ? t('connections.createTitle') : t('connections.editTitle'),
    size: 'lg',
    centered: true,
    closeOnClickOutside: false,
    children: <Inner />,
  });
}
