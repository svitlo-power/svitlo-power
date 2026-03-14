import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { ActionIcon, Alert, Box, Group, Loader, SimpleGrid, Stack, Text, Title, useMantineColorScheme } from "@mantine/core";
import { FC, useMemo } from "react";
import { toLocalDateTime } from "../../../utils";
import { DayOutageSchedule } from "./dayOutageSchedule";
import { OutagesScheduleData } from "../../../stores/types";
import dayjs from "dayjs";
import { TFunction } from "i18next";

type PlannedOutagesProps = {
  t: TFunction;
  outageQueue: string;
  data: OutagesScheduleData;
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
};

export const PlannedOutages: FC<PlannedOutagesProps> = ({ t, outageQueue, data, loading, error, onRefresh }) => {
  const { colorScheme } = useMantineColorScheme();
  const isDark = colorScheme === "dark";

  const days = useMemo(() => {
    if (!data?.days || data.days.length === 0) return [];
    
    const now = dayjs();
    const today = now.startOf('day');
    
    return data.days.map(day => {
      const dayDate = dayjs(day.date);
      const isToday = dayDate.isSame(today, 'day');
      const isTomorrow = dayDate.isSame(today.add(1, 'day'), 'day');
      
      let title = dayDate.format('dddd, MMMM D');
      if (isToday) title = `${t('day.today')} (${dayDate.format('MMM D')})`;
      if (isTomorrow) title = `${t('day.tomorrow')} (${dayDate.format('MMM D')})`;

      return {
        title,
        data: day,
        isToday,
      };
    }).sort((a, b) => {
      return dayjs(a.data.date).unix() - dayjs(b.data.date).unix();
    });
  }, [data, t]);

  if (loading) {
    return (
      <Box ta="center" py="xl">
        <Loader size="lg" />
        <Text mt="md" c="dimmed">
          {t('outages.loading')}
        </Text>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert color="red" title="Error">
        {error}
      </Alert>
    );
  }

  if (!data?.days || data.days.length === 0) {
    return (
      <Box ta="center" py="xl">
        <Alert color="yellow" title={t('outages.noData')}>
          <Stack gap="sm">
            <Text size="sm">
              {t('outages.error')}
            </Text>
            <Group justify="center">
              <ActionIcon
                variant="light"
                color="blue"
                size="lg"
                onClick={() => onRefresh()}
                disabled={loading}
              >
                <Box
                  style={{
                    animation: loading ? "spin 1s linear infinite" : "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <FontAwesomeIcon icon="refresh" />
                </Box>
              </ActionIcon>
            </Group>
          </Stack>
        </Alert>
      </Box>
    );
  }

  return (
    <Stack gap="lg">
      <Group justify="center" align="center" gap="md">
        <Title order={2} ta='center'>
          {t('outages.title', { outageQueue })}
        </Title>
      </Group>
      <style>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>

      <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="lg">
        {days.map((day, idx) => (
          <DayOutageSchedule
            t={t}
            key={`day-${idx}-${day.data.date}`}
            title={day.title} 
            isDark={isDark} 
            dayData={day.data} 
            isToday={day.isToday} 
          />
        ))}
      </SimpleGrid>

      {/* Updated On */}
      {data?.updatedOn && (
        <Text size="xs" c="dimmed" ta="center">
          {t('outages.lastUpdated', { time: toLocalDateTime(data.updatedOn) })}
        </Text>
      )}
    </Stack>
  );
};