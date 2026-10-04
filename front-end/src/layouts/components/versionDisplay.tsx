import { FC } from "react";
import { selectAppVersion } from "../../stores/selectors";
import { useAppSelector } from "../../stores/store";
import { Box, em } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";

type VersionDisplayProps = {
  compact?: boolean;
};

export const VersionDisplay: FC<VersionDisplayProps> = ({ compact = false }) => {
  const version = useAppSelector(selectAppVersion);
  const isMobile = useMediaQuery(`(max-width: ${em(750)})`);
  const lh = compact || isMobile ? "xs" : "var(--app-shell-footer-height)";

  return <Box fz="xs" ta="center" lh={lh}>
      <span
        data-testid="navbar-version-label"
        style={{ color: "var(--mantine-color-dimmed)", fontSize: 11, fontWeight: 500, opacity: 0.2 }}
      >
        v{version}
      </span>
    </Box>;
}