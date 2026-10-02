import { FC } from "react";
import { selectAppVersion } from "../../stores/selectors";
import { useAppSelector } from "../../stores/store";
import { Box, em, Text } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";

export const VersionDisplay: FC = () => {
  const version = useAppSelector(selectAppVersion);
  const isMobile = useMediaQuery(`(max-width: ${em(750)})`);
  const lh = isMobile ? "xs" : "var(--app-shell-footer-height)";

  return <Box fz="xs" ta="center" lh={lh}>
      <Text lh={lh} fz={11} fw={500} c="dimmed" data-testid="navbar-version-label">
        v{version}
      </Text>
    </Box>;
}