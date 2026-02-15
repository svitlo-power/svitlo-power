import { FC, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { connect } from "react-redux";
import { RootState, useAppDispatch } from "../../stores/store";
import { cancelPasswordReset, cancelUsersEditing, createUser, CreateUserResponse, deleteUser, deleteUserToken, fetchUsers, generateUserToken, requestPasswordReset, saveUsers } from "../../stores/thunks";
import { cancelCreatingUser, startCreatingUser, updateUser } from "../../stores/slices";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { createSelector } from "@reduxjs/toolkit";
import { UserItem, UserReportMode } from "../../stores/types";
import { DataTable, ErrorMessage, Page } from "../../components";
import { ColumnDataType } from "../../types";
import { Badge, Button, Code, ComboboxItem, CopyButton, Group, Modal, Select, Stack, Switch, Tabs, Text, Textarea, TextInput } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { modals } from "@mantine/modals";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { generatePasswordResetLink, getApiBaseUrl, getCurlExample, getCurlExampleOneLine, getHomeAssistantExample, integrationNotes } from "../../utils";
import { ObjectId } from "../../schemas";
import { usePageTranslation } from "../../utils";


type ComponentProps = {
  users: Array<UserItem>;
  loading: boolean;
  error: string | null;
  changed: boolean;
  creating: boolean;
};

const selectUsers = (state: RootState) => state.users.users;

const selectChanged = createSelector(
  [selectUsers],
  (users) => users.some(u => u.changed)
);

const mapStateToProps = (state: RootState): ComponentProps => ({
  users: state.users.users,
  loading: state.users.loading,
  error: state.users.error,
  changed: selectChanged(state),
  creating: state.users.creating,
});

const Component: FC<ComponentProps> = ({ users, loading, error, changed }: ComponentProps) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation('users');
  const [opened, { open, close }] = useDisclosure(false);
  const [tokenModalOpened, { open: openTokenModal, close: closeTokenModal }] = useDisclosure(false);
  const [integrationModalOpened, { open: openIntegrationModal, close: closeIntegrationModal }] = useDisclosure(false);
  const [editingUser, setEditingUser] = useState<UserItem | null>(null);
  const [viewingToken, setViewingToken] = useState<string | null>(null);
  const [viewingTokenUser, setViewingTokenUser] = useState<UserItem | null>(null);
  const [formData, setFormData] = useState<UserItem>({ id: '', name: '', isReporter: false, isActive: true, changed: true, });

  const fetchData = useCallback(() => dispatch(fetchUsers()), [dispatch]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  
  const openCreateDialog = useCallback(() => {
    setEditingUser(null);
    setFormData({ id: '', name: '', isReporter: false, isActive: true, changed: true, });
    dispatch(startCreatingUser());
    open();
  }, [dispatch, open]);

  const openEditDialog = useCallback((user: UserItem) => {
    setEditingUser(user);
    setFormData({ id: user.id, name: user.name, isReporter: user.isReporter, isActive: user.isActive, reportMode: user.reportMode, changed: user.changed, });
    open();
  }, [open]);

  const handleSave = useCallback(() => {
    if (editingUser) {
      dispatch(updateUser({
        id: editingUser.id,
        name: formData.name,
        isReporter: formData.isReporter,
        isActive: formData.isActive,
        reportMode: formData.reportMode,
      }));
      close();
    } else {
      // Create new user - will get reset token in response
      dispatch(createUser({
        name: formData.name,
        isReporter: formData.isReporter,
      }))
        .unwrap()
        .then((result: CreateUserResponse) => {
          close();
          if (result.resetToken && !formData.isReporter) {
            const baseUrl = getApiBaseUrl();
            const link = baseUrl + generatePasswordResetLink(formData.name, result.resetToken);
            modals.open({
              title: t('modal.userCreatedTitle'),
              size: "lg",
              children: <>
                <Text size="sm" mb="md">
                  {t('modal.userCreatedMessage', { name: formData.name })}
                </Text>
                <Text size="sm" fw={500} mb="xs">
                  <FontAwesomeIcon icon="share" /> {t('modal.userCreatedShare')}
                </Text>
                <Textarea 
                  value={link} 
                  autosize 
                  minRows={3}
                  styles={{
                    input: {
                      fontFamily: 'monospace',
                      fontSize: '12px',
                    }
                  }}
                  readOnly
                  onClick={(e) => e.currentTarget.select()}
                />
                <Text c='red.8' mt="md" size="sm">
                  <FontAwesomeIcon icon="exclamation-triangle" />
                  &nbsp;{t('modal.userCreatedExpiration')}
                </Text>
                <Group justify="space-between" mt="xl">
                  <CopyButton value={link}>
                    {({ copied, copy }) => (
                      <Button                    
                        leftSection={<FontAwesomeIcon icon={copied ? 'check' : 'copy'} />}
                        color={copied ? 'teal' : 'blue'}
                        onClick={copy}
                        variant={copied ? 'light' : 'filled'}
                      >
                        {copied ? t('button.linkCopied') : t('button.copyLink')}
                      </Button>
                    )}
                  </CopyButton>
                  <Button variant="default" onClick={() => modals.closeAll()}>
                    {t('button.close')}
                  </Button>
                </Group>
              </>
            });
          }
        });
    }
  }, [editingUser, dispatch, formData.name, formData.isReporter, formData.isActive, formData.reportMode, close, t]);

  const handleCancel = useCallback(() => {
    if (!editingUser) {
      dispatch(cancelCreatingUser());
    }
    close();
  }, [editingUser, dispatch, close]);

  const handleDelete = useCallback((user: UserItem) => {
    modals.openConfirmModal({
      title: t('modal.deleteUserTitle'),
      children: t('modal.deleteUserConfirm', { name: user.name }),
      labels: { confirm: t('button.delete'), cancel: t('button.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => dispatch(deleteUser(user.id)),
    });
  }, [dispatch, t]);

  const handleGenerateToken = useCallback((user: UserItem) => {
    modals.openConfirmModal({
      title: t('modal.generateTokenTitle'),
      children: user.apiKey 
        ? t('modal.generateTokenConfirmExisting', { name: user.name })
        : t('modal.generateTokenConfirm', { name: user.name }),
      labels: { confirm: t('button.generate'), cancel: t('button.cancel') },
      confirmProps: { color: 'blue' },
      onConfirm: () => dispatch(generateUserToken(user.id)),
    });
  }, [dispatch, t]);

  const handleDeleteToken = useCallback((user: UserItem) => {
    modals.openConfirmModal({
      title: t('modal.deleteTokenTitle'),
      children: t('modal.deleteTokenConfirm', { name: user.name }),
      labels: { confirm: t('button.delete'), cancel: t('button.cancel') },
      confirmProps: { color: 'red' },
      onConfirm: () => dispatch(deleteUserToken(user.id)),
    });
  }, [dispatch, t]);

  const handleViewToken = useCallback((user: UserItem) => {
    setViewingToken(user.apiKey || null);
    setViewingTokenUser(user);
    openTokenModal();
  }, [openTokenModal]);

  const handleDeleteFromModal = useCallback(() => {
    if (viewingTokenUser) {
      closeTokenModal();
      handleDeleteToken(viewingTokenUser);
    }
  }, [viewingTokenUser, closeTokenModal, handleDeleteToken]);

  const handleShowIntegration = useCallback(() => {
    openIntegrationModal();
  }, [openIntegrationModal]);

  const getHeaderButtons = useCallback((dataChanged: boolean): PageHeaderButton[] => [
    { text: t('form.create'), icon: "add", color: "teal", onClick: () => openCreateDialog(), disabled: false, },
    { text: t('button.save'), icon: "save", color: "green", onClick: () => dispatch(saveUsers()), disabled: !dataChanged, },
    { text: t('button.cancel'), icon: "cancel", color: "black", onClick: () => dispatch(cancelUsersEditing()), disabled: !dataChanged, },
  ], [openCreateDialog, dispatch, t]);

  const { setHeaderButtons, updateButtonAttributes } = useHeaderContent();
  const updateButtonAttributesRef = useRef(updateButtonAttributes);
  
  useEffect(() => {
    updateButtonAttributesRef.current = updateButtonAttributes;
  });

  useEffect(() => {
    setHeaderButtons(getHeaderButtons(false));
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons]);

  useEffect(() => {
    updateButtonAttributesRef.current(1, { disabled: !changed });
    updateButtonAttributesRef.current(2, { disabled: !changed });
  }, [changed]);

  const reportModeOptions: ComboboxItem[] = useMemo(() =>
    Object.values(UserReportMode).map(m => ({
      label: t(`reportMode.${m}`),
      value: m,
    })), [t]);

  if (error) {
    return <ErrorMessage content={error}/>;
  }

  const onUserActiveChange = (id: ObjectId, isActive: boolean) => {
    dispatch(updateUser({ id, isActive }));
  };
  
  const onUserReporterChange = (id: ObjectId, isReporter: boolean) => {
    dispatch(updateUser({ id, isReporter }));
  };

  const handleChangePassword = () => {
    if (editingUser) {
      dispatch(requestPasswordReset(editingUser.name))
        .unwrap()
        .then((token) => {
          close();
          const baseUrl = getApiBaseUrl();
          const link = baseUrl + generatePasswordResetLink(editingUser.name, token);
          const id = modals.open({
            title: t('modal.passwordResetTitle'),
            size: "lg",
            children: <>
              <Text size="sm" mb="md">
                {t('modal.passwordResetMessage', { name: editingUser.name })}
              </Text>
              <Text size="sm" fw={500} mb="xs">
                <FontAwesomeIcon icon="share" /> {t('modal.passwordResetShare')}
              </Text>
              <Textarea 
                value={link} 
                autosize 
                minRows={3}
                styles={{
                  input: {
                    fontFamily: 'monospace',
                    fontSize: '12px',
                  }
                }}
                readOnly
                onClick={(e) => e.currentTarget.select()}
              />
              <Text c='red.8' mt="md" size="sm">
                <FontAwesomeIcon icon="exclamation-triangle" />
                &nbsp;{t('modal.userCreatedExpiration')}
              </Text>
              <Group justify="space-between" mt="xl">
                <Group>
                  <CopyButton value={link}>
                    {({ copied, copy }) => (
                      <Button
                        leftSection={<FontAwesomeIcon icon={copied ? 'check' : 'copy'} />}
                        color={copied ? 'teal' : 'blue'}
                        onClick={copy}
                        variant={copied ? 'light' : 'filled'}
                      >
                        {copied ? t('button.linkCopied') : t('button.copyLink')}
                      </Button>
                    )}
                  </CopyButton>
                  <Button
                    variant="light"
                    color="red"
                    onClick={() => {
                      modals.openConfirmModal({
                        title: t('modal.cancelPasswordResetTitle'),
                        children: t('modal.cancelPasswordResetConfirm', { name: editingUser.name }),
                        labels: { confirm: t('form.cancelReset'), cancel: t('button.close') },
                        confirmProps: { color: 'red' },
                        onConfirm: () => {
                          modals.close(id);
                          dispatch(cancelPasswordReset(editingUser.name));
                        },
                      });
                    }}
                  >
                    <FontAwesomeIcon icon="times" />
                    &nbsp;{t('form.cancelReset')}
                  </Button>
                </Group>
                <Button variant="default" onClick={() => modals.close(id)}>
                  {t('button.close')}
                </Button>
              </Group>
            </>
          });
        });
    }
  }

  return <>
    <Page loading={loading}>
      <DataTable<UserItem>
        data={users}
        fetchAction={fetchData}
        defSort={[{ id: 'name', desc: false }]}
        columns={[
              {
                id: 'name',
                header: t('table.username'),
                enableSorting: true,
                accessorKey: 'name',
                meta: {
                  dataType: ColumnDataType.Text,
                },
              },
          {
            id: 'isActive',
            header: t('table.active'),
            enableSorting: false,
            accessorKey: 'isActive',
            meta: {
              dataType: ColumnDataType.Boolean,
              readOnly: false,
              checkedChange: (row, state) => onUserActiveChange(row.id!, state),
            },
          },
          {
            id: 'isReporter',
            header: t('table.isReporter'),
            enableSorting: false,
            accessorKey: 'isReporter',
            meta: {
              dataType: ColumnDataType.Boolean,
              readOnly: false,
              checkedChange: (row, state) => onUserReporterChange(row.id!, state),
            },
          },
          {
            id: 'apiKey',
            header: t('table.apiToken'),
            enableSorting: false,
            accessorKey: 'apiKey',
            cell: ({ row }) => {
              const user = row.original;
              
              if (!user.isReporter) {
                return (
                  <Badge 
                    variant="light"
                    color="gray"
                  >
                    {t('badge.na')}
                  </Badge>
                );
              }
              
              if (!user.apiKey) {
                if (changed) {
                  return (
                    <Badge 
                      variant="light"
                      color="orange"
                      style={{ cursor: 'not-allowed' }}
                      title={t('misc.saveChangesBeforeGenerating')}
                    >
                      {t('badge.saveFirst')}
                    </Badge>
                  );
                }
                return (
                  <Badge 
                    variant="light"
                    color="green"
                    style={{ cursor: 'pointer' }}
                    onClick={() => handleGenerateToken(user)}
                  >
                    {t('badge.generateToken')}
                  </Badge>
                );
              }
              return (
                <Badge 
                  variant="light"
                  color="blue"
                  style={{ cursor: 'pointer' }}
                  onClick={() => handleViewToken(user)}
                >
                  {t('badge.showToken')}
                </Badge>
              );
            },
          },
          {
            id: 'actions',
            meta: {
              dataType: 'actions',
              actions: [
                {
                  icon: 'edit',
                  color: 'blue',
                  text: t('actions.edit'),
                  onlyIcon: true,
                  clickHandler: (row) => openEditDialog(row),
                },
                {
                  icon: 'trash',
                  color: 'red',
                  text: t('actions.delete'),
                  onlyIcon: true,
                  clickHandler: (row) => handleDelete(row),
                },
              ],
            },
          },
        ]}
        tableKey={"users"}
      />
    </Page>

      <Modal opened={opened} onClose={handleCancel} title={editingUser ? t('modal.editUserTitle') : t('modal.createUserTitle')}>
      <Stack>
        <TextInput
          label={t('form.usernameLabel')}
          placeholder={t('form.usernamePlaceholder')}
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
        />
        <Switch
          label={t('form.activeLabel')}
          checked={formData.isActive}
          onChange={(e) => setFormData({ ...formData, isActive: e.currentTarget.checked })}
        />
        <Switch
          label={t('form.isReporterLabel')}
          checked={formData.isReporter}
          onChange={(e) => setFormData({ ...formData, isReporter: e.currentTarget.checked })}
        />
        { formData.isReporter && <Select
            label={t('form.reportMode')}
            data={reportModeOptions}
            value={formData.reportMode}
            allowDeselect={false}
            onChange={(e) => setFormData({ ...formData, reportMode: e as UserReportMode })}
          /> }
        <Group justify="space-between" mt="md">
          {editingUser && <Button
              disabled={formData.isReporter}
              onClick={handleChangePassword}
            >
              {t('form.changePassword')}
            </Button>}
          <Group justify="flex-end" ml="auto">
            <Button variant="default" onClick={handleCancel}>{t('button.close')}</Button>
            <Button onClick={handleSave} disabled={!formData.name}>
              {editingUser ? t('form.update') : t('form.create')}
            </Button>
          </Group>
        </Group>
      </Stack>
    </Modal>

    <Modal opened={tokenModalOpened} onClose={closeTokenModal} title={t('modal.apiTokenTitle')} size="lg">
      <Stack>
        <TextInput
          label={t('modalExtra.fullTokenLabel')}
          value={viewingToken || ''}
          readOnly
          styles={{
            input: {
              fontFamily: 'monospace',
              fontSize: '12px',
              cursor: 'text',
              userSelect: 'all',
            }
          }}
          onClick={(e) => e.currentTarget.select()}
        />
        <Group justify="space-between" mt="md">
          <Group>
            <Button
              leftSection={<FontAwesomeIcon icon="trash" />}
              color="red"
              variant="light"
              onClick={handleDeleteFromModal}
            >
              {t('button.delete')}
            </Button>
            <Button
              leftSection={<FontAwesomeIcon icon="code" />}
              color="violet"
              variant="light"
              onClick={handleShowIntegration}
            >
              {t('button.showIntegration')}
            </Button>
          </Group>
          <Group>
            <CopyButton value={viewingToken || ''}>
              {({ copied, copy }) => (
                <Button
                  leftSection={<FontAwesomeIcon icon={copied ? 'check' : 'copy'} />}
                  color={copied ? 'teal' : 'blue'}
                  onClick={copy}
                >
                  {copied ? t('button.copied') : t('button.copy')}
                </Button>
              )}
            </CopyButton>
            <Button variant="default" onClick={closeTokenModal}>{t('button.close')}</Button>
          </Group>
        </Group>
      </Stack>
    </Modal>

    <Modal opened={integrationModalOpened} onClose={closeIntegrationModal} title={t('integration.title')} size="xl">
      <Tabs defaultValue="curl">
        <Tabs.List>
          <Tabs.Tab value="curl" leftSection={<FontAwesomeIcon icon="terminal" />}>
            {t('integration.curl.title')}
          </Tabs.Tab>
          <Tabs.Tab value="homeassistant" leftSection={<FontAwesomeIcon icon="home" />}>
            {t('integration.homeassistant.title')}
          </Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="curl" pt="md">
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              {t(integrationNotes.curl.descriptionKey)}
            </Text>
            <Code block style={{ position: 'relative' }}>
              {getCurlExample(viewingToken || 'YOUR_API_TOKEN')}
            </Code>
            <CopyButton value={getCurlExampleOneLine(viewingToken || 'YOUR_API_TOKEN')}>
              {({ copied, copy }) => (
                <Button
                  fullWidth
                  leftSection={<FontAwesomeIcon icon={copied ? 'check' : 'copy'} />}
                  color={copied ? 'teal' : 'blue'}
                  onClick={copy}
                >
                  {copied ? t('button.copied') : t('integration.copyCurl')}
                </Button>
              )}
            </CopyButton>
            <Text size="xs" c="dimmed">
              {t('integration.note')} {t(integrationNotes.curl.noteKey)}
            </Text>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="homeassistant" pt="md">
          <Stack gap="md">
            <Text size="sm" c="dimmed">
              {t(integrationNotes.homeAssistant.descriptionKey)}
            </Text>
            <Code block>
              {getHomeAssistantExample(viewingToken || 'YOUR_API_TOKEN')}
            </Code>
            <CopyButton value={getHomeAssistantExample(viewingToken || 'YOUR_API_TOKEN')}>
              {({ copied, copy }) => (
                <Button
                  fullWidth
                  leftSection={<FontAwesomeIcon icon={copied ? 'check' : 'copy'} />}
                  color={copied ? 'teal' : 'blue'}
                  onClick={copy}
                >
                  {copied ? t('button.copied') : t('integration.copyHA')}
                </Button>
              )}
            </CopyButton>
            <Text size="xs" c="dimmed">
              {t('integration.note')} {t(integrationNotes.homeAssistant.noteKey)}
            </Text>
          </Stack>
        </Tabs.Panel>
      </Tabs>
      <Group justify="flex-end" mt="xl">
        <Button variant="default" onClick={closeIntegrationModal}>{t('button.close')}</Button>
      </Group>
    </Modal>
  </>
}

export const UsersPage = connect(mapStateToProps)(Component);

