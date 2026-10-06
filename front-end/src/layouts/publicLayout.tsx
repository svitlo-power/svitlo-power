import { FC, ReactNode, useEffect, useState } from "react";
import { Anchor, AppShell, Box, Container, Group, Image, SimpleGrid, Stack, Transition, useMantineColorScheme, Button, Menu, ActionIcon } from "@mantine/core";
import { CountryFlag, LangPicker, ThemePicker } from "../components";
import classes from './styles/publicLayout.module.css';
import { VisitTracker } from "./components/visitTracker";
import { Authors } from "./components/authors";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import iconDark from "../assets/icon_dark_with_text.png";
import iconLight from "../assets/icon_light_with_text.png";
import { usePageTranslation } from "../utils";
import { useSubscribeEvent } from "../hooks";
import { EventType } from "../types";
import { VersionDisplay } from "./components/versionDisplay";
import { useTranslation } from "react-i18next";

type PublicLayoutProps = {
  children: ReactNode;
};

export const PublicLayout: FC<PublicLayoutProps> = ({ children }) => {
  const [isAltPressed, setIsAltPressed] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const { colorScheme } = useMantineColorScheme();
  const iconSrc = colorScheme === 'dark' ? iconLight : iconDark;

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.altKey) {
      setIsAltPressed(true);
    }
  };

  const handleKeyUp = (e: KeyboardEvent) => {
    if (!e.altKey) {
      setTimeout(() => setIsAltPressed(false), 4000);
    }
  };

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, []);

  useSubscribeEvent(EventType.Shutdown, () => {
    setTimeout(() => {
      window.location.reload();
    }, 5000);
  });

  const t = usePageTranslation('common');
  const { t: privacyPolicyT } = useTranslation('privacyPolicy');
  const currentYear = new Date().getFullYear();

  return <AppShell
      header={{ height: 60 }}
      layout="default"
    >
      <AppShell.Header
          onMouseEnter={() => setIsHovering(true)}
          onMouseLeave={() => setIsHovering(false)}>
        <header className={classes.header}>
          <Container size="md" className={classes.inner}>
            <Group justify="flex-start" align="center">
              <Anchor href="/" underline="never">
                <Image h={35} w={160} src={iconSrc} alt="Logo" />
              </Anchor>
              <Transition transition="slide-down" mounted={isHovering && isAltPressed}>
                {(transitionStyles) => (
                  <Anchor
                    style={transitionStyles}
                    href="/login"
                  >
                    <FontAwesomeIcon icon='sign-in'/>
                    Log in
                  </Anchor>
                )}
              </Transition>
            </Group>
            <Group gap="md">
              <Anchor href="/app" underline="never">
                <Button 
                  variant="light" 
                  leftSection={<FontAwesomeIcon icon="mobile" />}
                  size="xs"
                  className={classes.downloadButton}
                >
                  {t('button.getApp')}
                </Button>
              </Anchor>
              <Box visibleFrom="md">
                <Group>
                  <Menu shadow="md" trigger="click">
                    <Menu.Target>
                      <Button px={6} variant="subtle" leftSection={<CountryFlag />}>
                        {t('title.language')}
                      </Button>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <LangPicker />
                    </Menu.Dropdown>
                  </Menu>
                  <ThemePicker isNavbarCollapsed={false} size="md" />
                </Group>
              </Box>
              <Box hiddenFrom="md">
                <Menu shadow="md" trigger="click">
                  <Menu.Target>
                    <ActionIcon variant="subtle" size="lg">
                      <FontAwesomeIcon icon="chevron-down" />
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <LangPicker iconPosition="left" />
                    <Menu.Divider />
                    <Box m='sm'>
                      <ThemePicker isNavbarCollapsed={false} size="md" />
                    </Box>
                  </Menu.Dropdown>
                </Menu>
              </Box>
            </Group>
          </Container>
        </header>
      </AppShell.Header>
      <AppShell.Main>
        <Box className={classes.main} pt="md" pb="md">
          {children}
        </Box>
        <footer className={classes.footer}>
          <SimpleGrid className={'mantine-AppShell-footer'} h="100%" verticalSpacing={0} spacing={0} p={0} ta="center" cols={{ base: 1, md: 3 }} style={{ alignItems: "center" }}>
            <Authors />
            <Stack gap={0} align="center" justify="center">
              <Group gap={6} justify="center" align="center">
                <Anchor href="/privacy-policy" size="xs">{privacyPolicyT('title')}</Anchor>
                <Box fz="xs">|</Box>
                <Box fz="xs">© Svitlo Power {currentYear}</Box>
              </Group>
              <VersionDisplay compact />
            </Stack>
            <VisitTracker />
          </SimpleGrid>
        </footer>
      </AppShell.Main>
    </AppShell>;
};
