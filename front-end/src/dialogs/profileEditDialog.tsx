import { FC, useEffect } from "react";
import { modals } from "@mantine/modals";
import { Button, Divider, Group, Stack, TextInput } from "@mantine/core";
import { useFormHandler } from "../hooks";
import { RootState, useAppDispatch, useAppSelector } from "../stores/store";
import { ProfileEdit, withUniqueNameValidation } from "../schemas";
import {
  fetchUsers,
  requestPasswordReset,
  saveProfile,
} from "../stores/thunks";
import { createSelector } from "@reduxjs/toolkit";
import {
  editProfile,
  finishEditingProfile,
  logout,
  startEditingProfile,
} from "../stores/slices";
import { shallowEqual } from "react-redux";
import { createSearchParams } from "react-router-dom";
import { TFunction } from "i18next";

export function openProfileEditDialog(t: TFunction) {
  type InnerProps = {
    profile: ProfileEdit;
    userNames: Array<string>;
    loading: boolean;
    t: TFunction;
  };

  const selectAuth = (state: RootState) => state.auth;
  const selectUsers = (state: RootState) => state.users;

  const selectLoading = createSelector(
    [selectAuth, selectUsers],
    (auth, users) => auth.loading || users.loading,
  );

  const selectUserNames = createSelector([selectUsers], (users) =>
    users.users.map((m) => m.name),
  );

  const mapStateToProps = (
    state: RootState,
    ownProps: { t: TFunction },
  ): InnerProps => ({
    profile: state.auth.editingProfile!,
    userNames: selectUserNames(state),
    loading: selectLoading(state),
    t: ownProps.t,
  });

  const Inner: FC<InnerProps> = ({ profile, userNames, loading, t }) => {
    const dispatch = useAppDispatch();

    useEffect(() => {
      dispatch(fetchUsers());
    }, [dispatch]);

    const schema = withUniqueNameValidation(userNames);

    const {
      renderField,
      handleFormSubmit,
      handleReset,
      isDirty,
      isValid,
      setValidationErrors,
    } = useFormHandler<ProfileEdit>({
      validationSchema: schema,
      fetchDataAction: () => {
        dispatch(startEditingProfile());
      },
      cleanupAction: () => {
        dispatch(finishEditingProfile());
      },
      formKey: "profile",
      isEdit: true,
      initialData: profile,
      loading: loading,
      saveAction: (data) => {
        dispatch(editProfile(data));
        dispatch(saveProfile());
      },
      useLocationGuard: false,
      defaultRender: (name, title, context) => {
        return (
          <TextInput
            required
            label={title}
            {...context.helpers.registerControl(name)}
          />
        );
      },
      fields: [
        {
          name: "userName",
          title: t ? t("profile.loginLabel") : "Login",
          required: true,
        },
      ],
    });

    const handleSave = () => {
      if (id) {
        modals.close(id);
      }
      handleFormSubmit();
    };

    const handleCancel = () => {
      if (id) {
        modals.close(id);
      }
      handleReset();
    };

    const handleChangePassword = () => {
      if (id) {
        modals.close(id);
      }
      const userName = profile.userName;
      dispatch(requestPasswordReset(userName))
        .unwrap()
        .then((token) => {
          const search = createSearchParams({
            username: userName,
            token: token,
          }).toString();
          const url = `/changePassword?${search}`;
          dispatch(logout());
          window.location.href = url;
        })
        .catch((error) => {
          setValidationErrors({ repeatNewPassword: error });
        });
    };

    return (
      <Stack>
        {renderField("userName")}
        <Divider />
        <Group justify="space-between">
          <Button
            color="orange"
            onClick={handleChangePassword}
            disabled={isDirty}
          >
            {t ? t("profile.changePassword") : "Change password"}
          </Button>
          <Group justify="flex-end">
            <Button onClick={handleSave} disabled={!isDirty || !isValid}>
              {t ? t("button.save") : "Save"}
            </Button>
            <Button variant="default" onClick={handleCancel}>
              {t ? t("button.cancel") : "Cancel"}
            </Button>
          </Group>
        </Group>
      </Stack>
    );
  };

  const ConnectedInner: FC<{ t: TFunction }> = (ownProps) => {
    const props = useAppSelector(
      (state) => mapStateToProps(state, ownProps),
      shallowEqual,
    );
    return <Inner {...props} />;
  };

  const id: string | undefined = modals.open({
    title: t("profile.editTitle"),
    centered: true,
    withCloseButton: false,
    closeOnClickOutside: false,
    closeOnEscape: false,
    children: <ConnectedInner t={t} />,
  });
}
