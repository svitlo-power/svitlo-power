import { Outlet, useLocation } from "react-router-dom";
import { FC, Suspense, useCallback, useEffect } from "react";
import { RootRoutes } from "../routes";
import { useHeaderContent } from "../providers";
import { useAppDispatch, useAppSelector } from "../stores/store";
import { AppShell } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import classes from "./styles/authenticatedLayout.module.css";
import { Header } from "./components/header";
import { Navbar } from "./components/navbar";
import useLocalStorage from "../hooks/useLocalStorage";
import { fetchProfile } from "../stores/thunks";
import { openProfileEditDialog } from "../dialogs";
import { authDataSelector } from "../stores/selectors";
import { EventType } from "../types";
import { logout } from "../stores/slices";
import { useTranslation } from "react-i18next";
import { useSubscribeEvent } from "../hooks";

export const AuthenticatedLayout: FC = () => {
  const authData = useAppSelector(authDataSelector);
  const profile = useAppSelector((state) => state.auth.profile);
  const dispatch = useAppDispatch();
  const { t } = useTranslation("common");

  const location = useLocation();

  useEffect(() => {
    if (authData?.accessToken && !profile) {
      dispatch(fetchProfile());
    }
  }, [authData, profile, dispatch]);

  const [opened, { toggle, close }] = useDisclosure();

  const { headerButtons, headerText } = useHeaderContent();

  const caption = headerText
    ? headerText
    : RootRoutes.find((f) => f.path === location.pathname)?.name;

  const [isNavbarCollapsed, setNavbarCollapsed] = useLocalStorage(
    "dmb-nv-collapsed",
    false,
  );
  const toggleNavbar = useCallback(() => {
    setNavbarCollapsed(!isNavbarCollapsed);
  }, [isNavbarCollapsed, setNavbarCollapsed]);

  const onLogoutClick = () => {
    dispatch(logout());
  };

  const onProfileEditClick = () => {
    openProfileEditDialog(t);
  };

  useSubscribeEvent(EventType.Shutdown, () => {
    setTimeout(() => {
      window.location.reload();
    }, 5000);
  });

  return (
    <AppShell
      classNames={{
        root: classes.root,
        navbar: classes.navbar,
        header: classes.header,
        main: classes.main,
      }}
      navbar={{
        width: isNavbarCollapsed ? 60 : 260,
        breakpoint: "md",
        collapsed: { mobile: !opened },
      }}
      layout="alt"
      transitionTimingFunction="step-start"
    >
      <AppShell.Header ms={0}>
        <Header
          t={t}
          user={profile}
          opened={opened}
          toggle={toggle}
          caption={caption!}
          buttons={headerButtons}
          onProfileClick={onProfileEditClick}
          onLogoutClick={onLogoutClick}
        />
      </AppShell.Header>
      <AppShell.Navbar data-collapsed={isNavbarCollapsed}>
        <Navbar
          t={t}
          user={profile}
          isNavbarCollapsed={isNavbarCollapsed}
          toggleNavbar={toggleNavbar}
          closeMenu={close}
          onProfileClick={onProfileEditClick}
          onLogoutClick={onLogoutClick}
        />
      </AppShell.Navbar>
      <AppShell.Main>
        <Suspense>{authData?.accessToken && profile && <Outlet />}</Suspense>
      </AppShell.Main>
    </AppShell>
  );
};
