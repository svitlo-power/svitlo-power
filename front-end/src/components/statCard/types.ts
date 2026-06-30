import { MantineColor, ProgressProps } from "@mantine/core";
import { ReactNode } from "react";

export type StatRow = {
  icon?: ReactNode;
  left: ReactNode;
  right?: ReactNode;
};

export type StatsCardProps = {
  christmasTree: boolean;
  title: string;
  bgColor: MantineColor;
  icon?: ReactNode;
  iconColor: MantineColor;
  progress: ProgressProps | null;
  onClick?: () => void;
  rows?: StatRow[];
  loading: boolean;
};