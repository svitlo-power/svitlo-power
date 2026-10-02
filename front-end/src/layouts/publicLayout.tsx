import { FC, ReactNode, useEffect, useState } from "react";
import { Anchor, AppShell, Box, Container, Group, Image, SimpleGrid, Transition, useMantineColorScheme, Button, Menu, ActionIcon, em } from "@mantine/core";
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
import { useMediaQuery } from "@mantine/hooks";

type PublicLayoutProps = {
  children: ReactNode;
};

export const PublicLayout: FC<PublicLayoutProps> = ({ children }) => {
  const [isAltPressed, setIsAltPressed] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const { colorScheme } = useMantineColorScheme();
  const iconSrc = colorScheme === 'dark' ? iconLight : iconDark;
  const isMobile = useMediaQuery(`(max-width: ${em(750)})`);

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
      layout="default"
      footer={{ height: 42 }}
    >
      <AppShell.Header
          onMouseEnter={() => setIsHovering(true)}
          onMouseLeave={() => setIsHovering(false)}>
        <header className={classes.header}>
          <Container size="md" className={classes.inner}>
            <Group justify="flex-start" align="center">
              <Image h={35} w={160} src={iconSrc} alt="Logo" />
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
                    { isMobile && <>
                    <Menu.Divider />
                    <VersionDisplay />
</> }
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
      </AppShell.Main>
      <AppShell.Footer>
        <SimpleGrid pt={2} verticalSpacing={0} spacing={0} p={0} ta={'center'} cols={{ xs: 1, md: isMobile ? 2 : 3}}>
          <Authors />
          <VisitTracker/>
          { !isMobile && <VersionDisplay /> }
        </SimpleGrid>
      </AppShell.Footer>
    </AppShell>;
};
