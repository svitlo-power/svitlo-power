import { FC, useEffect } from "react";
import { login } from "../stores/thunks";
import { useAppDispatch, useAppSelector } from "../stores/store";
import { useLocation, useNavigate } from "react-router-dom";
import { Button, PasswordInput, TextInput } from "@mantine/core";
import { useFormHandler } from "../hooks";
import { loginSchema, LoginType } from "../schemas";
import { useLoading } from "../providers";
import { ErrorMessage } from "../components";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { authDataSelector } from "../stores/selectors";
import { useTranslation } from "react-i18next";

export const LoginPage: FC = () => {
  const loading = useAppSelector((state) => state.auth.loading);
  const error = useAppSelector((state) => state.auth.error);
  const authData = useAppSelector(authDataSelector);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const { setLoading } = useLoading();
  const { t } = useTranslation();

  const returnUrl =
    new URLSearchParams(location.search).get("returnUrl") || "/";

  useEffect(() => {
    if (authData?.accessToken) {
      navigate("/");
    }
  }, [authData, navigate]);

  useEffect(() => {
    if (authData?.accessToken) {
      navigate(returnUrl.endsWith("notAllowed") ? "/" : returnUrl, {
        replace: true,
      });
    }
  }, [authData, returnUrl, navigate]);

  useEffect(() => {
    setLoading(loading);
  }, [loading, setLoading]);

  const changePassword = async (data: LoginType) => {
    dispatch(
      login({
        userName: data.userName,
        password: data.password,
      }),
    );
  };

  const { handleFormSubmit, registerControl, isValid } =
    useFormHandler<LoginType>({
      formKey: "login",
      isEdit: false,
      cleanupAction: () => {},
      fetchDataAction: () => {},
      saveAction: changePassword,
      validationSchema: loginSchema,
      errorFormatter: (error) => t(error),
    });

  return (
    <form onSubmit={handleFormSubmit}>
      <TextInput
        placeholder={t("userName")}
        required
        radius="md"
        leftSection={<FontAwesomeIcon icon={"user-md"} />}
        {...registerControl("userName")}
      />
      <PasswordInput
        placeholder={t("password")}
        required
        mt="md"
        radius="md"
        leftSection={<FontAwesomeIcon icon={"key"} />}
        {...registerControl("password")}
      />
      <ErrorMessage content={error} ta="center" size="sm" />

      <Button type="submit" fullWidth mt="xl" radius="md" disabled={!isValid}>
        {t("logIn")}
      </Button>
    </form>
  );
};
