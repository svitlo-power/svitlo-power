import { FC, useEffect } from "react";
import { modals } from "@mantine/modals";
import { Button, Divider, Group, Stack, TextInput } from "@mantine/core";
import { useFormHandler } from "../hooks";
import { useAppDispatch, useAppSelector } from "../stores/store";
import { ProfileEdit, withUniqueNameValidation } from "../schemas";
import {
  fetchUsers,
  requestPasswordReset,
  saveProfile,
} from "../stores/thunks";
import {
  editProfile,
  finishEditingProfile,
  logout,
  startEditingProfile,
} from "../stores/slices";
import { createSearchParams } from "react-router-dom";
import { TFunction } from "i18next";
import {
  selectProfileEditLoading,
  selectProfileEditUserNames,
} from "../stores/selectors";

export function openProfileEditDialog(t: TFunction) {
  const Inner: FC<{ t: TFunction }> = ({ t }) => {
    const profile = useAppSelector((state) => state.auth.editingProfile!);
    const userNames = useAppSelector(selectProfileEditUserNames);
    const loading = useAppSelector(selectProfileEditLoading);
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

  const id: string | undefined = modals.open({
    title: t("profile.editTitle"),
    centered: true,
    withCloseButton: false,
    closeOnClickOutside: false,
    closeOnEscape: false,
    children: <Inner t={t} />,
  });
}
