import { FC, useCallback, useEffect, useMemo } from "react";
import { StationDataItem } from "../../stores/types";
import { RootState, useAppDispatch, useAppSelector } from "../../stores/store";
import { StationChartCard } from "./components";
import { shallowEqual } from "react-redux";
import { fetchStationsData } from "../../stores/thunks";
import { ErrorMessage } from "../../components";
import {
  Box,
  ComboboxItem,
  InputLabel,
  Select,
  SimpleGrid,
} from "@mantine/core";
import useLocalStorage from "../../hooks/useLocalStorage";
import { initGA, trackPageView } from "../../utils/analytics";
import { usePageTranslation } from "../../utils";
import { TFunction } from "i18next";
import { DateRange, EventType } from "../../types";
import dayjs from "dayjs";
import DateRangePicker from "../../components/dateRangePicker";
import { useSubscribeEvent } from "../../hooks";

type ComponentProps = {
  stationsData: Array<StationDataItem>;
  loading: boolean;
  error: string | null;
};

const mapStateToProps = (state: RootState): ComponentProps => ({
  stationsData: state.stationsData.stationsData,
  error: state.stationsData.error,
  loading: state.stationsData.loading,
});

const buildIntervalOptions = (t: TFunction): ComboboxItem[] => [
  { label: t("interval.last15"), value: "900" },
  { label: t("interval.last30"), value: "1800" },
  { label: t("interval.last1h"), value: "3600" },
  { label: t("interval.last3h"), value: (3600 * 3).toString() },
  { label: t("interval.last6h"), value: (3600 * 6).toString() },
  { label: t("interval.lastDay"), value: (3600 * 12).toString() },
  { label: t("interval.lastTwoDays"), value: (3600 * 24).toString() },
  { label: t("interval.custom"), value: "custom" },
];

const Component: FC<ComponentProps> = ({ stationsData, loading, error }) => {
  const dispatch = useAppDispatch();
  const t = usePageTranslation("home");
  const [dataInterval, setDataInterval] = useLocalStorage<string | "custom">(
    "home_graphs_interval",
    "1800",
  );
  const [customRange, setCustomRange] = useLocalStorage<DateRange>(
    "home_graphs_custom_range",
    {
      from: dayjs().utc().add(-1, "day").toDate(),
      to: dayjs().utc().toDate(),
    },
  );
  const intervalOptions = useMemo(() => buildIntervalOptions(t), [t]);
  const isCustomRange = useMemo(
    () => dataInterval === "custom",
    [dataInterval],
  );

  const fetchData = useCallback(() => {
    const action =
      isCustomRange && customRange.from && customRange.to
        ? () =>
            dispatch(
              fetchStationsData({
                value: null,
                startDate: customRange.from!,
                endDate: customRange.to!,
              }),
            )
        : () =>
            dispatch(
              fetchStationsData({
                value: parseInt(dataInterval),
                startDate: null,
                endDate: null,
              }),
            );
    action();
  }, [customRange.from, customRange.to, dataInterval, dispatch, isCustomRange]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData, 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Google Analytics
  useEffect(() => {
    initGA();
    trackPageView("/", "Home Page");
  }, []);

  const onDataIntervalChange = (_: unknown, option: ComboboxItem) => {
    if (option.value === "custom") {
      setDataInterval(option.value);
      return;
    }
    const interval = parseInt(option.value);
    setDataInterval(interval.toString());
  };

  const onCustomRangeChange = (value: DateRange | string) => {
    const range = value as DateRange;
    if (range?.from && range?.to) {
      range.to = dayjs(range.to).utc().add(1, "day").add(-1, "second").toDate();
      setCustomRange(range);
    }
  };

  useSubscribeEvent(EventType.StationDataUpdated, () => {
    fetchData();
  });

  if (error) {
    return <ErrorMessage content={error} />;
  }

  return (
    <>
      <SimpleGrid cols={{ base: 1, sm: 2, md: 2, lg: 4 }}>
        <Select
          label={t("label.interval")}
          value={dataInterval}
          data={intervalOptions}
          onChange={onDataIntervalChange}
        />
        {isCustomRange && (
          <Box>
            <InputLabel>{t("label.customInterval")}</InputLabel>
            <DateRangePicker
              value={customRange}
              onChange={onCustomRangeChange}
            />
          </Box>
        )}
      </SimpleGrid>
      {!error &&
        stationsData.map((data) => (
          <StationChartCard
            t={t}
            loading={loading}
            key={`st_data_${data.id}`}
            data={data}
          />
        ))}
      {error && <ErrorMessage content={error} />}
    </>
  );
};

const ConnectedComponent: FC = () => {
  const props = useAppSelector(mapStateToProps, shallowEqual);
  return <Component {...props} />;
};

export const HomePage = ConnectedComponent;
