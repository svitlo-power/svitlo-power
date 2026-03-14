import { Badge, Card, Divider, Group, Stack, Text } from "@mantine/core";
import { FC, useMemo } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { minutesToHoursAndMinutes } from "../../../utils";
import { DayData, DayDataStatus } from "../../../stores/types";
import { OutageSlot } from "./outageSlot";
import { Placeholder } from "./outageSchedulePlaceholder";
import { TFunction } from "i18next";

type DayOutageScheduleProps = {
  t: TFunction;
  title: string;
  isDark: boolean;
  dayData?: DayData;
  isToday?: boolean;
};

export const DayOutageSchedule: FC<DayOutageScheduleProps> = ({ t, isDark, dayData, title, isToday = false }) => {
  const slots = useMemo(
    () => (dayData?.slots ?? []),
    [dayData],
  );
  const summaryOutageTime = useMemo(
    () => slots?.reduce((prev, curr) => prev += (curr.end - curr.start), 0),
    [slots],
  );
  const isAvailable = useMemo(
    () => dayData?.status === DayDataStatus.ScheduleApplies && slots.length > 0,
    [dayData?.status, slots],
  );
  const isEmergency = useMemo(
    () => dayData?.status === DayDataStatus.EmergencyShutdowns,
    [dayData?.status],
  );
  const isWaitingForSchedule = useMemo(
    () => dayData?.status === DayDataStatus.WaitingForSchedule,
    [dayData?.status],
  );

  return (
    <Card shadow="sm" padding="lg" radius="md" withBorder>
      <Stack gap="md" h='100%'>
        <Group justify="space-between" align="center">
          <Text fw={600} size="lg">
            {title}
          </Text>
          {isAvailable && <Group gap={'xs'}>
            <Badge color="red" variant="light">
              {slots.length}
            </Badge>
            <Badge color="red" variant="light">
              <FontAwesomeIcon icon='clock' />
              {minutesToHoursAndMinutes(summaryOutageTime)}
            </Badge>
          </Group>}
        </Group>
        <Divider />
        <Stack gap="xs" justify="center" h='100%'>
          { isWaitingForSchedule && 
            <Placeholder
              text={t('outages.waitingForSchedule')}
              icon='hourglass'
              color="dimmed"
            />
          }
          { isEmergency &&
            <Placeholder
              text={t('outages.emergency')}
              icon='triangle-exclamation'
              color="orange"
            />
          }
          { !isAvailable && !isWaitingForSchedule && !isEmergency &&
            <Placeholder
              text={t('outages.noShutdowns')}
              icon='check'
              color="green"
            />
          }
          {isAvailable && slots.map((slot, idx) => (
            <OutageSlot t={t} key={`outage_${idx}`} isDark={isDark} slot={slot} isToday={isToday} />
          ))}
        </Stack>
      </Stack>
    </Card>    
  );
};