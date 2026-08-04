import { FC, useEffect } from "react";
import { TFunction } from "i18next";
import { connect } from "react-redux";
import { modals } from "@mantine/modals";
import { ActionIcon, Button, Center, Group, Loader, Stack, Table, Text, Tooltip } from "@mantine/core";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { RootState, useAppDispatch } from "../../../stores/store";
import { ServerStationConnectionItem } from "../../../stores/types";
import { deleteStationConnection, fetchStationConnections } from "../../../stores/thunks";
import { ErrorMessage } from "../../../components";
import { openConnectionEditDialog } from "./connectionEditDialog";

type OpenConnectionsDialogOptions = {
  t: TFunction;
};

export function openConnectionsDialog({ t }: OpenConnectionsDialogOptions) {
  type InnerProps = {
    connections: Array<ServerStationConnectionItem>;
    loading: boolean;
    error: string | null;
  };

  const mapStateToProps = (state: RootState): InnerProps => ({
    connections: state.stationConnections.connections,
    loading: state.stationConnections.loading,
    error: state.stationConnections.error,
  });

  const Inner: FC<InnerProps> = ({ connections, loading, error }) => {
    const dispatch = useAppDispatch();

    useEffect(() => {
      dispatch(fetchStationConnections());
    }, [dispatch]);

    const handleDelete = (connection: ServerStationConnectionItem) => {
      modals.openConfirmModal({
        title: t('connections.deleteTitle'),
        centered: true,
        children: (
          <Text size="sm">
            {t('connections.deleteConfirm', { name: connection.name })}
          </Text>
        ),
        labels: { confirm: t('button.delete'), cancel: t('button.cancel') },
        confirmProps: { color: 'red' },
        onConfirm: () => dispatch(deleteStationConnection(connection.id)),
      });
    };

    return (
      <Stack>
        {error && <ErrorMessage content={error} />}
        {loading && connections.length === 0 ? (
          <Center py="lg">
            <Loader />
          </Center>
        ) : (
          <Table>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t('connections.table.name')}</Table.Th>
                <Table.Th>{t('connections.table.email')}</Table.Th>
                <Table.Th ta="center">{t('connections.table.syncOnPoll')}</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {connections.map((connection) => (
                <Table.Tr key={connection.id}>
                  <Table.Td>{connection.name}</Table.Td>
                  <Table.Td>{connection.email}</Table.Td>
                  <Table.Td ta="center">
                    {connection.syncStationsOnPoll && <FontAwesomeIcon icon="check" />}
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" justify="flex-end" wrap="nowrap">
                      <Tooltip label={t('button.edit')}>
                        <ActionIcon
                          color="teal"
                          onClick={() => openConnectionEditDialog({ connection, t })}
                        >
                          <FontAwesomeIcon icon="edit" />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label={t('button.delete')}>
                        <ActionIcon
                          color="red"
                          onClick={() => handleDelete(connection)}
                        >
                          <FontAwesomeIcon icon="trash" />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        )}
        <Group justify="space-between">
          <Button
            leftSection={<FontAwesomeIcon icon="add" />}
            onClick={() => openConnectionEditDialog({ create: true, t })}
          >
            {t('connections.add')}
          </Button>
          <Button variant="default" onClick={handleClose}>
            {t('button.close')}
          </Button>
        </Group>
      </Stack>
    );
  };

  const handleClose = () => {
    if (id) {
      modals.close(id);
    }
  };

  const ConnectedInner = connect(mapStateToProps)(Inner);

  const id: string | undefined = modals.open({
    title: t('connections.title'),
    size: 'lg',
    centered: true,
    children: <ConnectedInner />,
  });
}
