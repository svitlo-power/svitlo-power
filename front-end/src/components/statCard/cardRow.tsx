import { Group, MantineColor, Text, ThemeIcon } from "@mantine/core";
import { FC } from "react";
import { StatRow } from "./types";

type StatCardRowProps = {
  row: StatRow;
  resolvedStatTextColor: MantineColor;
  iconColor: MantineColor;
};

export const StatCardRow: FC<StatCardRowProps> = ({ row, resolvedStatTextColor, iconColor }) => {
  return <Group w="100%" p="apart" align="center" gap="sm" >
      <Group align="center" gap="xs">
        {row.icon && (
          <ThemeIcon
            c={resolvedStatTextColor}
            size="sm"
            color={iconColor}
            radius="xl"
            style={{ background: 'transparent' }}
          >
            {row.icon}
          </ThemeIcon>
        )}
        <Text c={resolvedStatTextColor} fw={600}>
          {row.left}
        </Text>
      </Group>

      {row.right && (
        <Text c={resolvedStatTextColor} fw={500}>
          {row.right}
        </Text>
      )}
    </Group>;
};