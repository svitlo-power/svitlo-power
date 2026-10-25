import { FC, useCallback, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAppDispatch, useAppSelector } from "../../stores/store";
import { ErrorMessage, Page } from "../../components";
import {
  Box,
  Card,
  Text,
  Grid,
  Stack,
  Group,
  Button,
  Select,
  Table,
  Badge,
  Paper,
  Title,
} from "@mantine/core";
import { AreaChart } from "@mantine/charts";
import { fetchStationDetails } from "../../stores/thunks";
import { clearStationDetails } from "../../stores/slices";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { toLocalDateTime } from "../../utils/dateUtils";
import { ObjectId } from "../../schemas";
import { usePageTranslation } from "../../utils";
import useLocalStorage from "../../hooks/useLocalStorage";

const StatCard: FC<{
  title: string;
  value: number;
  unit: string;
  color: string;
}> = ({ title, value, unit, color }) => (
  <Paper p="md" withBorder>
    <Stack gap="xs">
      <Text size="sm" c="dimmed">
        {title}
      </Text>
      <Text size="xl" fw={700} c={color}>
        {value.toFixed(2)} {unit}
      </Text>
    </Stack>
  </Paper>
);

export const StationDetailsPage: FC = () => {
  const detailsData = useAppSelector(
    (state) => state.stationsData.stationDetails,
  );
  const loading = useAppSelector((state) => state.stationsData.detailsLoading);
  const error = useAppSelector((state) => state.stationsData.detailsError);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { stationId } = useParams<{ stationId: ObjectId }>();
  const t = usePageTranslation("stations");

  // 24 hours default
  const [timeRange, setTimeRange] = useLocalStorage<string>(
    `station_details_${stationId}`,
    "86400",
  );

  const fetchData = useCallback(() => {
    if (stationId) {
      dispatch(
        fetchStationDetails({
          stationId: stationId,
          lastSeconds: parseInt(timeRange),
        }),
      );
    }
  }, [dispatch, stationId, timeRange]);

  useEffect(() => {
    fetchData();
    return () => {
      dispatch(clearStationDetails());
    };
  }, [fetchData, dispatch]);

  const goBack = () => {
    navigate("/stations");
  };

  const chartData = useMemo(() => {
    if (!detailsData?.data) return [];

    return detailsData.data.map((d) => ({
      time: toLocalDateTime(d.lastUpdateTime).split(" ")[1].substring(0, 5),
      batterySoc: d.batterySoc ?? 0,
      batteryPower: (d.batteryPower ?? 0) / 1000,
      chargePower: Math.abs((d.chargePower ?? 0) / 1000),
      dischargePower: (d.dischargePower ?? 0) / 1000,
      consumptionPower: (d.consumptionPower ?? 0) / 1000,
      generationPower: (d.generationPower ?? 0) / 1000,
      gridPower: (d.gridPower ?? 0) / 1000,
      irradiateIntensity: d.irradiateIntensity ?? 0,
    }));
  }, [detailsData]);

  const statistics = useMemo(() => {
    if (!detailsData?.data || detailsData.data.length === 0) {
      return null;
    }

    const data = detailsData.data;
    const validData = data.filter((d) => d.lastUpdateTime);

    const calcStats = (values: (number | null)[]) => {
      const validValues = values.filter(
        (v): v is number => v !== null && !isNaN(v),
      );
      if (validValues.length === 0)
        return { min: 0, max: 0, avg: 0, current: 0 };

      return {
        min: Math.min(...validValues),
        max: Math.max(...validValues),
        avg: validValues.reduce((a, b) => a + b, 0) / validValues.length,
        current: validValues[validValues.length - 1] || 0,
      };
    };

    return {
      dataPoints: validData.length,
      timeRange:
        validData.length > 1
          ? `${toLocalDateTime(validData[0].lastUpdateTime)} - ${toLocalDateTime(
              validData[validData.length - 1].lastUpdateTime,
            )}`
          : "N/A",
      batterySoc: calcStats(data.map((d) => d.batterySoc)),
      batteryPower: calcStats(data.map((d) => d.batteryPower)),
      chargePower: calcStats(data.map((d) => d.chargePower)),
      dischargePower: calcStats(data.map((d) => d.dischargePower)),
      consumptionPower: calcStats(data.map((d) => d.consumptionPower)),
      generationPower: calcStats(data.map((d) => d.generationPower)),
      gridPower: calcStats(data.map((d) => d.gridPower)),
      irradiateIntensity: calcStats(data.map((d) => d.irradiateIntensity)),
    };
  }, [detailsData]);

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <Page loading={loading}>
      <Stack gap="md" p="10px">
        {/* Header */}
        <Group justify="space-between">
          <Button
            leftSection={<FontAwesomeIcon icon="arrow-left" />}
            variant="light"
            onClick={goBack}
          >
            {t("back")}
          </Button>
          <Select
            label={t("timeRange.label")}
            value={timeRange}
            onChange={(value) => setTimeRange(value || "86400")}
            data={[
              { value: "3600", label: t("timeRange.options.lastHour") },
              { value: "21600", label: t("timeRange.options.last6h") },
              { value: "43200", label: t("timeRange.options.last12h") },
              { value: "86400", label: t("timeRange.options.last24h") },
              { value: "172800", label: t("timeRange.options.last2Days") },
              { value: "604800", label: t("timeRange.options.lastWeek") },
            ]}
            style={{ width: 200 }}
          />
        </Group>

        {detailsData && (
          <>
            {/* Station Info Card */}
            <Card withBorder radius="md" p="lg">
              <Title order={2} mb="md">
                {detailsData.station.stationName}
              </Title>
              <Grid>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.stationId")}
                  </Text>
                  <Text fw={500}>{detailsData.station.stationId}</Text>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.connectionStatus")}
                  </Text>
                  <Badge
                    color={
                      detailsData.station.connectionStatus === "online"
                        ? "green"
                        : "red"
                    }
                  >
                    {detailsData.station.connectionStatus}
                  </Badge>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.gridType")}
                  </Text>
                  <Text fw={500}>
                    {detailsData.station.gridInterconnectionType || "N/A"}
                  </Text>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.installedCapacity")}
                  </Text>
                  <Text fw={500}>
                    {detailsData.station.installedCapacity || 0}{" "}
                    {t("units.kW") ?? "kW"}
                  </Text>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.batteryCapacity")}
                  </Text>
                  <Text fw={500}>
                    {detailsData.station.batteryCapacity || 0}{" "}
                    {t("units.kWh") ?? "kWh"}
                  </Text>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.lastUpdate")}
                  </Text>
                  <Text fw={500}>
                    {detailsData.station.lastUpdateTime
                      ? toLocalDateTime(detailsData.station.lastUpdateTime)
                      : "N/A"}
                  </Text>
                </Grid.Col>
                <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                  <Text size="sm" c="dimmed">
                    {t("stationInfo.recordsProcessed")}
                  </Text>
                  <Text fw={700} size="lg" c="blue">
                    {detailsData.dataCount}
                  </Text>
                </Grid.Col>
              </Grid>
            </Card>

            {chartData.length > 0 && statistics ? (
              <>
                {/* Current Stats */}
                <Title order={3}>{t("currentValues")}</Title>
                <Grid>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <StatCard
                      title={t("stat.batterySoc")}
                      value={statistics.batterySoc.current}
                      unit={t("units.percent") ?? "%"}
                      color="blue"
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <StatCard
                      title={t("stat.generationPower")}
                      value={statistics.generationPower.current / 1000}
                      unit={t("units.kW") ?? "kW"}
                      color="green"
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <StatCard
                      title={t("stat.consumptionPower")}
                      value={statistics.consumptionPower.current / 1000}
                      unit={t("units.kW") ?? "kW"}
                      color="orange"
                    />
                  </Grid.Col>
                  <Grid.Col span={{ base: 12, sm: 6, md: 3 }}>
                    <StatCard
                      title={t("stat.gridPower")}
                      value={statistics.gridPower.current / 1000}
                      unit={t("units.kW") ?? "kW"}
                      color="violet"
                    />
                  </Grid.Col>
                </Grid>

                {/* Power Charts */}
                <Card withBorder radius="md" p="md">
                  <Title order={4} mb="md">
                    {t("charts.powerDetails")}
                  </Title>
                  <Box style={{ height: 300 }}>
                    <AreaChart
                      data={chartData}
                      dataKey="time"
                      series={[
                        {
                          name: "generationPower",
                          label: t("charts.series.generation"),
                          color: "green.6",
                        },
                        {
                          name: "consumptionPower",
                          label: t("charts.series.consumption"),
                          color: "orange.6",
                        },
                        {
                          name: "chargePower",
                          label: t("charts.series.charge"),
                          color: "cyan.6",
                        },
                        {
                          name: "dischargePower",
                          label: t("charts.series.discharge"),
                          color: "red.6",
                        },
                      ]}
                      withLegend
                      withTooltip
                      unit=" kW"
                      h="100%"
                      strokeWidth={2}
                      withDots={false}
                      gridProps={{ strokeDasharray: "3 2" }}
                    />
                  </Box>
                </Card>

                {/* Battery SOC Chart */}
                <Card withBorder radius="md" p="md">
                  <Title order={4} mb="md">
                    {t("charts.batterySoc")}
                  </Title>
                  <Box style={{ height: 250 }}>
                    <AreaChart
                      data={chartData}
                      dataKey="time"
                      series={[
                        {
                          name: "batterySoc",
                          label: t("charts.series.batterySoc"),
                          color: "blue.6",
                        },
                      ]}
                      withLegend
                      withTooltip
                      unit="%"
                      h="100%"
                      withGradient
                      withDots={false}
                      fillOpacity={0.6}
                      gridProps={{ strokeDasharray: "3 2" }}
                      yAxisProps={{ domain: [0, 100] }}
                    />
                  </Box>
                </Card>

                {/* Statistics Table */}
                <Card withBorder radius="md" p="md">
                  <Title order={4} mb="md">
                    {t("summary.title")}
                  </Title>
                  <Table.ScrollContainer minWidth={500}>
                    <Table striped highlightOnHover>
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t("summary.columns.parameter")}</Table.Th>
                          <Table.Th>{t("summary.columns.current")}</Table.Th>
                          <Table.Th>{t("summary.columns.average")}</Table.Th>
                          <Table.Th>{t("summary.columns.minimum")}</Table.Th>
                          <Table.Th>{t("summary.columns.maximum")}</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        <Table.Tr>
                          <Table.Td>{t("summary.params.batterySoc")}</Table.Td>
                          <Table.Td>
                            {statistics.batterySoc.current.toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {statistics.batterySoc.avg.toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {statistics.batterySoc.min.toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {statistics.batterySoc.max.toFixed(2)}
                          </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td>
                            {t("summary.params.generationPower")}
                          </Table.Td>
                          <Table.Td>
                            {(
                              statistics.generationPower.current / 1000
                            ).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.generationPower.avg / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.generationPower.min / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.generationPower.max / 1000).toFixed(2)}
                          </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td>
                            {t("summary.params.consumptionPower")}
                          </Table.Td>
                          <Table.Td>
                            {(
                              statistics.consumptionPower.current / 1000
                            ).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.consumptionPower.avg / 1000).toFixed(
                              2,
                            )}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.consumptionPower.min / 1000).toFixed(
                              2,
                            )}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.consumptionPower.max / 1000).toFixed(
                              2,
                            )}
                          </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td>{t("summary.params.chargePower")}</Table.Td>
                          <Table.Td>
                            {(
                              Math.abs(statistics.chargePower.current) / 1000
                            ).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(
                              Math.abs(statistics.chargePower.avg) / 1000
                            ).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(
                              Math.abs(statistics.chargePower.min) / 1000
                            ).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(
                              Math.abs(statistics.chargePower.max) / 1000
                            ).toFixed(2)}
                          </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td>
                            {t("summary.params.dischargePower")}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.dischargePower.current / 1000).toFixed(
                              2,
                            )}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.dischargePower.avg / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.dischargePower.min / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.dischargePower.max / 1000).toFixed(2)}
                          </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td>{t("summary.params.gridPower")}</Table.Td>
                          <Table.Td>
                            {(statistics.gridPower.current / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.gridPower.avg / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.gridPower.min / 1000).toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {(statistics.gridPower.max / 1000).toFixed(2)}
                          </Table.Td>
                        </Table.Tr>
                        <Table.Tr>
                          <Table.Td>{t("summary.params.irradiance")}</Table.Td>
                          <Table.Td>
                            {statistics.irradiateIntensity.current.toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {statistics.irradiateIntensity.avg.toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {statistics.irradiateIntensity.min.toFixed(2)}
                          </Table.Td>
                          <Table.Td>
                            {statistics.irradiateIntensity.max.toFixed(2)}
                          </Table.Td>
                        </Table.Tr>
                      </Table.Tbody>
                    </Table>
                  </Table.ScrollContainer>
                </Card>
              </>
            ) : (
              <Card withBorder radius="md" p="lg">
                <Text ta="center" c="dimmed">
                  {t("noData")}
                </Text>
              </Card>
            )}
          </>
        )}
      </Stack>
    </Page>
  );
};
