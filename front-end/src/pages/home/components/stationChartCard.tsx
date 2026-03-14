import { FC, useMemo, ReactNode } from "react";
import { StationDataItem, StationDataRecord } from "../../../stores/types";
import { Card, Text, Box, LoadingOverlay } from "@mantine/core";
import { AreaChart } from "@mantine/charts";
import { TFunction } from "i18next";
import i18n from "../../../i18n";
import { Payload } from "recharts/types/component/DefaultTooltipContent";

type StationChartCardProps = {
  data: StationDataItem;
  loading: boolean;
  t?: TFunction;
};

type StationDataChartRecord = StationDataRecord & {
  time: string;
  tooltipTime: string;
};

export const StationChartCard: FC<StationChartCardProps> = ({ data, loading, t }) => {
  const formatAxisTime = (value: Date) => new Date(value).toLocaleTimeString(i18n.language, { hour12: false });
  const formatTooltipTime = (value: Date) =>
    new Date(value).toLocaleString(i18n.language, {
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

  const dataArray = useMemo(() => data?.data ?? [], [data]);
  const dataLength = dataArray.length;

  const processedData: Array<StationDataChartRecord> = useMemo(
    () =>
      dataArray.map((d: StationDataRecord) => ({
        ...d,
        time: formatAxisTime(d.date),
        tooltipTime: formatTooltipTime(d.date),
      })),
    [dataArray],
  );

  const powerSeries = useMemo(
    () => [
      {
        name: 'chargePower',
        label: t ? t('chart.chargePower') : 'Charge power',
        color: '#1BFFC2',
      },
      {
        name: 'dischargePower',
        label: t ? t('chart.dischargePower') : 'Discharge power',
        color: '#FF3838',
      },
      {
        name: 'consumptionPower',
        label: t ? t('chart.consumptionPower') : 'Consumption power',
        color: '#FFC225',
      },
    ],
    [t],
  );

  const socSeries = useMemo(
    () => [
      {
        name: 'batterySoc',
        label: t ? t('chart.batterySoc') : 'Battery SOC',
        color: '#67C2FE',
      },
    ],
    [t],
  );

  const labelFormatter = (
    _: ReactNode,
    p: ReadonlyArray<Payload<keyof StationDataChartRecord, keyof StationChartCardProps>>
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
  ): ReactNode => p.length > 0 ? (p[0].payload as any)['tooltipTime'] : null;

  return (
    <Card withBorder radius="md" p="sm" mt="sm" style={{ width: '100%' }}>
      <LoadingOverlay visible={loading} />
      <Box style={{ marginBottom: 8 }}>
        <Text style={{ fontWeight: 600 }}>{data.name}</Text>
      </Box>

      {dataLength === 0 ? (
        <Box style={{ textAlign: 'center', color: 'var(--mantine-color-dimmed, #888)' }}>
          {t ? t('chart.noData') : 'No data!'}
        </Box>
      ) : (
        <div>
          <Box style={{ height: 240 }}>
            <AreaChart
              data={processedData}
              dataKey="time"
              series={powerSeries}
              withLegend
              withTooltip
              unit="kW"
              h="100%"
              valueFormatter={(v: number) => `${v / 1000}`}
              strokeWidth={2}
              withDots={false}
              yAxisProps={{
                domain: [0, 100],
              }}
              tooltipProps={{
                labelFormatter: labelFormatter,
              }}
              gridProps={{ strokeDasharray: '3 2' }}
              areaChartProps={{ syncId: String(data.id) }}
            />
          </Box>

          <Box style={{ height: 240, marginTop: 8 }}>
            <AreaChart
              data={processedData}
              dataKey="time"
              series={socSeries}
              withLegend
              withTooltip
              h="100%"
              unit="%"
              withGradient
              withDots={false}
              fillOpacity={0.6}
              tooltipProps={{
                labelFormatter: labelFormatter,
              }}
              gridProps={{ strokeDasharray: '3 2' }}
              areaChartProps={{ syncId: String(data.id) }}
            />
          </Box>
        </div>
      )}
    </Card>
  );
};