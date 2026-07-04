import { FC, useCallback, useEffect, useMemo, useRef } from "react";
import {
  Container,
  Title,
  Stack,
  Group,
} from "@mantine/core";
import { useDocumentVisibility } from "@mantine/hooks";
import { RootState, useAppDispatch, useAppSelector } from "../../stores/store";
import { fetchBuildings, fetchBuildingsSummary, fetchDashboardConfig, fetchOutagesSchedule, saveBuildings, saveDashboardConfig } from "../../stores/thunks";
import { BuildingsView, openDashboardEditDialog, PlannedOutages } from "./components";
import { BuildingListItem, BuildingSummaryItem, DashboardConfig, OutagesScheduleData } from "../../stores/types";
import { connect } from "react-redux";
import { IconButton } from "../../components";
import { PageHeaderButton, useHeaderContent } from "../../providers";
import { BuildingEditType } from "../../schemas";
import { authDataSelector, createSelectEdittedBuildings } from "../../stores/selectors";
import { initGA, trackPageView } from "../../utils/analytics";
import { useLocalizedEffect, useSubscribeEvents } from "../../hooks";
import { usePageTranslation } from "../../utils";
import i18n from "../../i18n";
import { EventItem, EventType } from "../../types";

type ComponentProps = {
  loadingConfig: boolean;
  loadingBuildings: boolean;
  loadingSummary: boolean;
  loadingOutagesSchedule: boolean;
  dashboardConfig?: DashboardConfig;
  buildings: Array<BuildingListItem | BuildingEditType>;
  buildingsSummary: Array<BuildingSummaryItem>;
  configChanged: boolean;
  buildingsChanged: boolean;
  outagesScheduleError: string | null;
  outagesSchedule: OutagesScheduleData;
  buildngsSummaryError: string | null;
};

const mapStateToProps = (state: RootState): ComponentProps => {
  return {
    loadingConfig: state.dashboardConfig.loading,
    loadingBuildings: state.buildings.loading,
    loadingSummary: state.buildingsSummary.loading,
    loadingOutagesSchedule: state.outagesSchedule.loading,
    configChanged: state.dashboardConfig.changed,
    dashboardConfig: state.dashboardConfig.config,
    buildingsChanged: state.buildings.changed,
    buildings: createSelectEdittedBuildings(state),
    buildingsSummary: state.buildingsSummary.items,
    outagesSchedule: state.outagesSchedule.outagesSchedule,
    outagesScheduleError: state.outagesSchedule.error,
    buildngsSummaryError: state.buildingsSummary.error,
  };
};

const Component: FC<ComponentProps> = ({
  loadingConfig,
  loadingBuildings,
  loadingSummary,
  loadingOutagesSchedule,
  buildings,
  buildingsSummary,
  dashboardConfig,
  configChanged,
  buildingsChanged,
  outagesSchedule,
  outagesScheduleError,
  buildngsSummaryError,
}) => {
  const isAuthenticated = Boolean(useAppSelector(authDataSelector)?.accessToken);
  const dispatch = useAppDispatch();

  const t = usePageTranslation('dashboard');

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

  const fetchSummary = useCallback((force: boolean = false) => {
    if (buildings && buildings.length > 0 && buildingsSummary.length === 0 && !buildngsSummaryError || force) {
      const buildingIds = buildings.map(m => m.id!);
      dispatch(fetchBuildingsSummary(buildingIds));
    }
  }, [buildings, buildingsSummary.length, buildngsSummaryError, dispatch]);

  useLocalizedEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const fetchOutages = useCallback(
    () => {
      if (dashboardConfig?.enableOutagesSchedule && dashboardConfig?.outagesScheduleQueue) {
        dispatch(fetchOutagesSchedule(dashboardConfig.outagesScheduleQueue));
      }
    },
    [dashboardConfig, dispatch]
  );

  useLocalizedEffect(() => {
    fetchOutages();
  }, [fetchOutages]);

  // Google Analytics
  useEffect(() => {
    initGA();
    trackPageView('/', 'Buildings Dashboard');
  }, []);

  const getHeaderButtons = useCallback((dataChanged: boolean): PageHeaderButton[] => [
    { text: t('button.save'), icon: "save", color: "green", onClick: saveData, disabled: !dataChanged, },
    { text: t('button.cancel'), icon: "cancel", color: "black", onClick: fetchData, disabled: !dataChanged, },
  ], [t, saveData, fetchData]);
  const { setHeaderButtons } = useHeaderContent();
  useLocalizedEffect(() => {
    setHeaderButtons(getHeaderButtons(configChanged || buildingsChanged));
    return () => setHeaderButtons([]);
  }, [setHeaderButtons, getHeaderButtons, configChanged, buildingsChanged]);

  const onEditDashboardClick = useCallback(() => {
    openDashboardEditDialog({
      dashboardConfig: dashboardConfig ?? {
        title: {
          en: '',
          uk: '',
        },
        enableOutagesSchedule: false,
        outagesScheduleQueue: '',
      },
      title: t('dashboardEdit.dialogTitle'),
    });
  }, [dashboardConfig, t]);

  const dashboardTitle = useMemo(() => {
    return dashboardConfig?.title[i18n.language] ?? dashboardConfig?.title['en'] ?? '<not set>'
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
    if (prevVisibility.current !== 'visible' && visibility === 'visible') {
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
      <Container size={"xl"} mih='100%'>
        <Stack gap={48} justify="space-between">
          <Group justify="center">
            {!loadingConfig && <Title pt='sm' order={1} ta="center" c="blue">
              {dashboardTitle}
            </Title>}
            {isAuthenticated && <IconButton
              icon='edit'
              color='blue'
              text={t('dashboardEdit.dialogTitle')}
              onClick={onEditDashboardClick}
            />}
          </Group>

          <BuildingsView
            t={t}
            loading={loadingBuildings}
            isAuthenticated={isAuthenticated}
            buildings={buildings}
            loadingSummary={loadingSummary}
            buildingsSummary={buildingsSummary}
          />

          {dashboardConfig?.enableOutagesSchedule && <PlannedOutages
            t={t}
            outageQueue={dashboardConfig.outagesScheduleQueue}
            data={outagesSchedule}
            loading={loadingOutagesSchedule}
            error={outagesScheduleError}
            onRefresh={fetchOutages}
          />}
        </Stack>
      </Container>
    </>
  );
};

export const BuildingsPage = connect(mapStateToProps)(Component);