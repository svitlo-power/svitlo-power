import { Box, Card, Flex, Group, ThemeIcon, useMantineTheme, useMantineColorScheme, getContrastColor, Title, alpha, lighten, parseThemeColor, Progress, LoadingOverlay } from "@mantine/core"
import { FC, useMemo, useState } from "react"
import classes from './styles/statCard.module.css';
import { SceneryContainer } from "./scenery";
import { StatsCardProps } from "./types";
import { StatCardRow } from "./cardRow";

export const StatsCard: FC<StatsCardProps> = ({
  christmasTree = false,
  title,
  bgColor,
  icon,
  iconColor,
  onClick,
  rows,
  progress,
  loading,
}) => {
  const theme = useMantineTheme();
  const { colorScheme } = useMantineColorScheme();
  const textColor = useMemo(
    () => getContrastColor({ color: bgColor, theme, autoContrast: true}),
    [bgColor, theme],
  );

  const resolvedCircleColor = useMemo(() => {
    const overlay = textColor === theme.white
      ? 'rgba(255,255,255,0.12)'
      : 'rgba(0,0,0,0.08)';
    return overlay;
  }, [textColor, theme]);

  const resolvedBgColor = useMemo(() => {
    const parsed = parseThemeColor({
      color: bgColor,
      theme,
      colorScheme,
    });
    return parsed.color;
  }, [bgColor, theme, colorScheme]);

  const resolvedStatBgColor = useMemo(() => {
    return lighten(
      alpha(resolvedBgColor, 0.5),
      1,
    );
  }, [resolvedBgColor]);

  const resolvedStatTextColor = useMemo(
    () => getContrastColor({
      color: resolvedStatBgColor,
      theme,
      autoContrast: true,
    }),
    [resolvedStatBgColor, theme],
  );

  const [hovered, setHovered] = useState(false);

  return (    
    <Card shadow="xs" padding="lg" radius="md"
      bg={resolvedBgColor}
      className={classes.cardHover}
        style={{
        cursor: onClick ? 'pointer' : 'default',
        overflow: 'hidden',
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <SceneryContainer christmasTree={christmasTree} hovered={hovered} />
      <Group justify="space-between" pos="relative">
        <Box style={{ borderColor: iconColor }}>
          <Group>
            <ThemeIcon className={classes.iconBox} color={iconColor} autoContrast radius="xl" size="sm">
              {icon}
            </ThemeIcon>
            <Title order={3} c={textColor}>{title}</Title>
          </Group>
        </Box>
        <Box
          className={classes.innerCircleBox}
          style={{ background: resolvedCircleColor, zIndex: 20, }}
        ></Box>
        <Box
          className={classes.outerCircleBox}
          style={{ background: resolvedCircleColor, zIndex: 21, }}
        ></Box>
      </Group>
      <Card.Section
        pt="lg"
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {progress && <Progress
          radius={0}
          styles={{
            root: {
              position: 'absolute',
              width: '100%',
              height: '15px',
              zIndex: 10,
            },
            section: {
              marginTop: '3px',
              height: '9px'
            }
          }}
          {...progress}
        />}
        <Flex
          mt="sm"
          w="100%"
          bg={resolvedStatBgColor}
          p={20}
          gap={8}
          direction="column"
          align="center"
          style={{
            flex: 1,
            position: 'relative',
          }}
        >
          <LoadingOverlay
            visible={loading}
            zIndex={1000}
            overlayProps={{ radius: 'sm', blur: 2 }}
            loaderProps={{ type: 'bars' }}
          />
          {rows?.map((row, i) => 
            <StatCardRow key={i}
              row={row}
              resolvedStatTextColor={resolvedStatTextColor}
              iconColor={iconColor}
            />)}
        </Flex>
      </Card.Section>
    </Card>
  );
}
