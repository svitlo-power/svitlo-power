import { FC, ReactNode, useEffect, useState } from "react";
import { Anchor, AppShell, Box, Container, Group, Image, Transition, useMantineColorScheme, Button, Menu, ActionIcon } from "@mantine/core";
import { CountryFlag, LangPicker, ThemePicker } from "../components";
import classes from './styles/publicLayout.module.css';
import { PublicFooter } from "./components/publicFooter";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import iconDark from "../assets/icon_dark_with_text.png";
import iconLight from "../assets/icon_light_with_text.png";
import { usePageTranslation } from "../utils";
import { useSubscribeEvent } from "../hooks";
import { EventType } from "../types";

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
  return <AppShell
      header={{ height: 60 }}
      footer={{ height: { base: 0, md: 40 } }}
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
        <Box component="footer" className={classes.footer} hiddenFrom="md" data-testid="mobile-public-footer">
          <PublicFooter />
        </Box>
      </AppShell.Main>
      <AppShell.Footer className={classes.footer} visibleFrom="md" data-testid="desktop-public-footer">
        <PublicFooter />
      </AppShell.Footer>
    </AppShell>;
};
