import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { Anchor, Box, em } from "@mantine/core";
import { useMediaQuery } from "@mantine/hooks";
import { FC } from "react";
import { Trans } from "react-i18next";

export const Authors: FC = () => {
  const isMobile = useMediaQuery(`(max-width: ${em(750)})`);

  return (
    <Box fz="xs">
      <Trans
        i18nKey="authors.label"
        components={[
          <Anchor
            size="xs"
            target="_blank"
            href="https://t.me/bearpawmaxim"
          >
            {!isMobile && <FontAwesomeIcon icon="user-md" />} @bearpawmaxim
          </Anchor>,
          <Anchor
            size="xs"
            target="_blank"
            href="https://t.me/gizmoboss"
          >
            {!isMobile && <FontAwesomeIcon icon="user-md" />} @gizmoboss
          </Anchor>,
        ]}
        values={{
          author1: "@bearpawmaxim",
          author2: "@gizmoboss",
        }}
      />
    </Box>
  );
};
