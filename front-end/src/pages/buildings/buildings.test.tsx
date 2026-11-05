import { createElement, useEffect } from "react";
import { Provider } from "react-redux";
import { render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { vi } from "vitest";
import { createTestStore } from "../../test/storeTestUtils";
import { EventItem, EventType } from "../../types";
import { setFeaturesLoaded } from "../../stores/slices/app";
import { BuildingsPage } from "./buildings";

const { mockGet, mockSetHeaderButtons, mockSubscribeEvents } = vi.hoisted(
  () => ({
    mockGet: vi.fn(),
    mockSetHeaderButtons: vi.fn(),
    mockSubscribeEvents: vi.fn(),
  }),
);

vi.mock("../../stores/store", async () => {
  const { useDispatch, useSelector } =
    await vi.importActual<typeof import("react-redux")>("react-redux");
  return { useAppDispatch: useDispatch, useAppSelector: useSelector };
});

vi.mock("../../utils/apiClient", () => ({
  default: { get: mockGet },
}));

vi.mock("../../hooks", () => ({
  useLocalizedEffect: (effect: () => void | (() => void), deps: unknown[]) =>
    useEffect(effect, deps),
  useSubscribeEvents: mockSubscribeEvents,
}));

vi.mock("../../providers", () => ({
  useHeaderContent: () => ({ setHeaderButtons: mockSetHeaderButtons }),
}));

vi.mock("../../utils", async () => {
  const actual =
    await vi.importActual<typeof import("../../utils")>("../../utils");
  return { ...actual, usePageTranslation: () => (key: string) => key };
});

vi.mock("../../utils/analytics", () => ({
  initGA: vi.fn(),
  trackPageView: vi.fn(),
}));

vi.mock("@mantine/hooks", async () => {
  const actual =
    await vi.importActual<typeof import("@mantine/hooks")>("@mantine/hooks");
  return { ...actual, useDocumentVisibility: () => "visible" };
});

vi.mock("./components", () => ({
  BuildingsView: () =>
    createElement("div", { "data-testid": "buildings-view" }),
  PlannedOutages: ({ outageQueue }: { outageQueue: string }) =>
    createElement("div", {
      "data-testid": "planned-outages",
      "data-queue": outageQueue,
    }),
  openDashboardEditDialog: vi.fn(),
}));

describe("BuildingsPage outage schedule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGet.mockImplementation((url: string) =>
      url.startsWith("/outagesSchedule/outagesSchedule/")
        ? Promise.resolve({ data: {} })
        : new Promise(() => {}),
    );
  });

  const renderPage = (
    outagesSchedule: {
      enable: boolean;
      regionId: number | string | null;
      dsoId: number | string | null;
      queue: string | null;
    } | null,
    featuresState = {
      backendRedisDashboardEnabled: false,
      featuresLoaded: false,
    },
  ) => {
    const store = createTestStore({
      app: {
        version: "0000.00.00",
        backendVersion: "0000.00.00",
        features: {
          backendRedisDashboardEnabled:
            featuresState.backendRedisDashboardEnabled,
        },
        featuresLoaded: featuresState.featuresLoaded,
      },
      dashboardConfig: {
        config: {
          title: { en: "Dashboard", uk: "Панель" },
          outagesSchedule,
        },
        loading: false,
        error: null,
        changed: false,
      },
    });

    render(
      <Provider store={store}>
        <MantineProvider>
          <BuildingsPage />
        </MantineProvider>
      </Provider>,
    );

    return store;
  };

  it("fetches and renders the configured outage queue", async () => {
    renderPage({ enable: true, regionId: 25, dsoId: 902, queue: "1.1" });

    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith(
        "/outagesSchedule/outagesSchedule/1.1",
      ),
    );
    expect(screen.getByTestId("planned-outages")).toHaveAttribute(
      "data-queue",
      "1.1",
    );
  });

  it.each([
    [
      "disabled schedule",
      { enable: false, regionId: null, dsoId: null, queue: null },
    ],
    ["missing queue", { enable: true, regionId: 25, dsoId: 902, queue: null }],
    ["missing schedule config", null],
  ])(
    "does not fetch or render outages for %s",
    async (_description, schedule) => {
      renderPage(schedule);

      await waitFor(() =>
        expect(mockGet).toHaveBeenCalledWith("/dashboard/config"),
      );
      expect(mockGet).not.toHaveBeenCalledWith(
        expect.stringContaining("/outagesSchedule/outagesSchedule/"),
      );
      expect(screen.queryByTestId("planned-outages")).not.toBeInTheDocument();
    },
  );

  it("waits for backend features before subscribing to refresh events", () => {
    renderPage(null);

    expect(mockSubscribeEvents).toHaveBeenLastCalledWith(
      expect.any(Function),
      false,
    );
  });

  it("refreshes dashboard data after backend features finish loading", async () => {
    const store = renderPage(null);
    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith("/dashboard/config"),
    );
    const initialRequestCount = mockGet.mock.calls.filter(
      ([url]) => url === "/dashboard/config",
    ).length;

    store.dispatch(setFeaturesLoaded());

    await waitFor(() => {
      expect(
        mockGet.mock.calls.filter(([url]) => url === "/dashboard/config")
          .length,
      ).toBeGreaterThan(initialRequestCount);
    });
  });

  it("uses only dashboard_updated in backend snapshot mode", () => {
    renderPage(null, {
      backendRedisDashboardEnabled: true,
      featuresLoaded: true,
    });

    const handler = mockSubscribeEvents.mock.calls.at(-1)?.[0] as (
      event: EventItem,
    ) => void;
    const previousCalls = mockGet.mock.calls.length;

    handler({
      type: EventType.BuildingsUpdated,
      data: {},
      private: false,
    });
    expect(mockGet).toHaveBeenCalledTimes(previousCalls);

    handler({
      type: EventType.DashboardUpdated,
      data: {},
      private: false,
    });
    expect(mockGet.mock.calls.length).toBeGreaterThan(previousCalls);
  });

  it("uses legacy dashboard events when backend snapshot mode is disabled", () => {
    renderPage(null, {
      backendRedisDashboardEnabled: false,
      featuresLoaded: true,
    });

    const handler = mockSubscribeEvents.mock.calls.at(-1)?.[0] as (
      event: EventItem,
    ) => void;
    const previousCalls = mockGet.mock.calls.length;

    handler({
      type: EventType.DashboardUpdated,
      data: {},
      private: false,
    });
    expect(mockGet).toHaveBeenCalledTimes(previousCalls);

    handler({
      type: EventType.BuildingsUpdated,
      data: {},
      private: false,
    });
    expect(mockGet.mock.calls.length).toBeGreaterThan(previousCalls);
  });
});
