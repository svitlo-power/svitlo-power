import { FC, useCallback, useEffect, useMemo, useRef } from "react";
import { Container, Title, Stack, Group } from "@mantine/core";
import { useDocumentVisibility } from "@mantine/hooks";
import { useAppDispatch, useAppSelector } from "../../stores/store";
import {
  fetchBuildings,
  fetchBuildingsSummary,
  fetchDashboardConfig,
  fetchOutagesSchedule,
  saveBuildings,
  saveDashboardConfig,
} from "../../stores/thunks";
import {
  BuildingsView,
  openDashboardEditDialog,
  PlannedOutages,
} from "./components";
import { IconButton } from "../../components";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import {
  authDataSelector,
  createSelectEdittedBuildings,
} from "../../stores/selectors";
import { initGA, trackPageView } from "../../utils/analytics";
import { useLocalizedEffect, useSubscribeEvents } from "../../hooks";
import { usePageTranslation } from "../../utils";
import i18n from "../../i18n";
import { EventItem, EventType } from "../../types";

export const BuildingsPage: FC = () => {
  const loadingConfig = useAppSelector(
    (state) => state.dashboardConfig.loading,
  );
  const loadingBuildings = useAppSelector((state) => state.buildings.loading);
  const loadingSummary = useAppSelector(
    (state) => state.buildingsSummary.loading,
  );
  const loadingOutagesSchedule = useAppSelector(
    (state) => state.outagesSchedule.loading,
  );
  const dashboardConfig = useAppSelector(
    (state) => state.dashboardConfig.config,
  );
  const configChanged = useAppSelector(
    (state) => state.dashboardConfig.changed,
  );
  const buildingsChanged = useAppSelector((state) => state.buildings.changed);
  const buildings = useAppSelector(createSelectEdittedBuildings);
  const buildingsSummary = useAppSelector(
    (state) => state.buildingsSummary.items,
  );
  const outagesSchedule = useAppSelector(
    (state) => state.outagesSchedule.outagesSchedule,
  );
  const outagesScheduleError = useAppSelector(
    (state) => state.outagesSchedule.error,
  );
  const buildngsSummaryError = useAppSelector(
    (state) => state.buildingsSummary.error,
  );
  const isAuthenticated = Boolean(
    useAppSelector(authDataSelector)?.accessToken,
  );
  const dispatch = useAppDispatch();

  const t = usePageTranslation("dashboard");

  const fetchData = useCallback(() => {
    dispatch(fetchBuildings());
    dispatch(fetchDashboardConfig());
  }, [dispatch]);

  const saveData = useCallback(() => {
    if (configChanged) {
      dispatch(saveDashboardConfig());
    }
    if (buildingsChanged) {
      dispatch(saveBuildings());
    }
  }, [configChanged, buildingsChanged, dispatch]);

  useLocalizedEffect(() => {
    fetchData();
  }, [fetchData]);

  const fetchSummary = useCallback(
    (force: boolean = false) => {
      if (
        (buildings &&
          buildings.length > 0 &&
          buildingsSummary.length === 0 &&
          !buildngsSummaryError) ||
        force
      ) {
        const buildingIds = buildings.map((m) => m.id!);
        dispatch(fetchBuildingsSummary(buildingIds));
      }
    },
    [buildings, buildingsSummary.length, buildngsSummaryError, dispatch],
  );

  useLocalizedEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const fetchOutages = useCallback(() => {
    const schedule = dashboardConfig?.outagesSchedule;
    if (schedule?.enable && schedule.queue) {
      dispatch(fetchOutagesSchedule(schedule.queue));
    }
  }, [dashboardConfig, dispatch]);

  useLocalizedEffect(() => {
    fetchOutages();
  }, [fetchOutages]);

  // Google Analytics
  useEffect(() => {
    initGA();
    trackPageView("/", "Buildings Dashboard");
  }, []);

  const getHeaderButtons = useCallback(
    (dataChanged: boolean): PageHeaderButton[] => [
      {
        text: t("button.save"),
        icon: "save",
        color: "green",
        onClick: saveData,
        disabled: !dataChanged,
      },
      {
        text: t("button.cancel"),
        icon: "cancel",
        color: "black",
        onClick: fetchData,
        disabled: !dataChanged,
      },
    ],
    [t, saveData, fetchData],
  );
  const { setHeaderButtons } = useHeaderContent();
  useLocalizedEffect(() => {
    setHeaderButtons(getHeaderButtons(configChanged || buildingsChanged));
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons, configChanged, buildingsChanged]);

  const onEditDashboardClick = useCallback(() => {
    openDashboardEditDialog({
      dashboardConfig: dashboardConfig ?? {
        title: {
          en: "",
          uk: "",
        },
        outagesSchedule: null,
      },
      title: t("dashboardEdit.dialogTitle"),
    });
  }, [dashboardConfig, t]);

  const dashboardTitle = useMemo(() => {
    return (
      dashboardConfig?.title[i18n.language] ??
      dashboardConfig?.title["en"] ??
      "<not set>"
    );
  }, [dashboardConfig?.title]);

  useSubscribeEvents((event: EventItem) => {
    switch (event.type) {
      case EventType.BuildingsUpdated:
      case EventType.DashboardConfigUpdated:
        fetchData();
        fetchSummary(true);
        fetchOutages();
        break;
      case EventType.ExtDataUpdated:
      case EventType.StationDataUpdated:
        fetchSummary(true);
        break;
      case EventType.OutagesUpdated:
        fetchOutages();
        break;
    }
  });

  const visibility = useDocumentVisibility();
  const prevVisibility = useRef(visibility);
  // eslint-disable-next-line react-hooks/purity
  const lastUpdateRef = useRef(Date.now());

  useEffect(() => {
    if (prevVisibility.current !== "visible" && visibility === "visible") {
      const now = Date.now();
      const fiveMinutes = 5 * 60 * 1000;
      if (now - lastUpdateRef.current > fiveMinutes) {
        fetchData();
        fetchSummary(true);
        fetchOutages();
        lastUpdateRef.current = now;
      }
    }
    prevVisibility.current = visibility;
  }, [visibility, fetchData, fetchSummary, fetchOutages]);

  return (
    <>
      <Container size={"xl"} mih="100%">
        <Stack gap={48} justify="space-between">
          <Group justify="center">
            {!loadingConfig && (
              <Title pt="sm" order={1} ta="center" c="blue">
                {dashboardTitle}
              </Title>
            )}
            {isAuthenticated && (
              <IconButton
                icon="edit"
                color="blue"
                text={t("dashboardEdit.dialogTitle")}
                onClick={onEditDashboardClick}
              />
            )}
          </Group>

          <BuildingsView
            t={t}
            loading={loadingBuildings}
            isAuthenticated={isAuthenticated}
            buildings={buildings}
            loadingSummary={loadingSummary}
            buildingsSummary={buildingsSummary}
          />

          {dashboardConfig?.outagesSchedule?.enable &&
            dashboardConfig.outagesSchedule.queue && (
              <PlannedOutages
                t={t}
                outageQueue={dashboardConfig.outagesSchedule.queue}
                data={outagesSchedule}
                loading={loadingOutagesSchedule}
                error={outagesScheduleError}
                onRefresh={fetchOutages}
              />
            )}
        </Stack>
      </Container>
    </>
  );
};
