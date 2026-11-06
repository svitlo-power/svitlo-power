import { createElement, useEffect } from "react";
import { Provider } from "react-redux";
import { act, render, screen, waitFor } from "@testing-library/react";
import { MantineProvider } from "@mantine/core";
import { vi } from "vitest";
import { createTestStore } from "../../test/storeTestUtils";
import { EventItem, EventType } from "../../types";
import { setFeaturesLoaded } from "../../stores/slices/app";
import { BuildingListItem } from "../../stores/types/buildings";
import { BuildingsPage } from "./buildings";

const { mockGet, mockPost, mockSetHeaderButtons, mockSubscribeEvents } =
  vi.hoisted(() => ({
    mockGet: vi.fn(),
    mockPost: vi.fn(),
    mockSetHeaderButtons: vi.fn(),
    mockSubscribeEvents: vi.fn(),
  }));

vi.mock("../../stores/store", async () => {
  const { useDispatch, useSelector } =
    await vi.importActual<typeof import("react-redux")>("react-redux");
  return { useAppDispatch: useDispatch, useAppSelector: useSelector };
});

vi.mock("../../utils/apiClient", () => ({
  default: { get: mockGet, post: mockPost },
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
    mockPost.mockResolvedValue({ data: [] });
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
      dashboardUpdatedEventEnabled: false,
      featuresLoaded: false,
    },
    hasUnsavedChanges = false,
    buildingItems: BuildingListItem[] = [],
  ) => {
    const store = createTestStore({
      app: {
        version: "0000.00.00",
        backendVersion: "0000.00.00",
        features: {
          dashboardUpdatedEventEnabled:
            featuresState.dashboardUpdatedEventEnabled,
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
        changed: hasUnsavedChanges,
      },
      buildings: {
        items: buildingItems,
        edittedItems: [],
        deletedItems: [],
        loading: false,
        error: null,
        changed: hasUnsavedChanges,
        globalId: 0,
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
      dashboardUpdatedEventEnabled: true,
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

  it("refreshes only the summary for summary-only snapshot updates", () => {
    renderPage(
      null,
      { dashboardUpdatedEventEnabled: true, featuresLoaded: true },
      false,
      [
        {
          id: "507f1f77bcf86cd799439011",
          name: { en: "Building", uk: "Будинок" },
          color: "blue",
          hasBoundStation: true,
          order: 1,
        },
      ],
    );
    const configRequests = mockGet.mock.calls.filter(
      ([url]) => url === "/dashboard/config",
    ).length;
    const buildingRequests = mockGet.mock.calls.filter(
      ([url]) => url === "/dashboard/buildings",
    ).length;
    const handler = mockSubscribeEvents.mock.calls.at(-1)?.[0] as (
      event: EventItem,
    ) => void;

    handler({
      type: EventType.DashboardUpdated,
      data: { changed: ["summary"] },
      private: false,
    });

    expect(mockPost).toHaveBeenCalledWith("/dashboard/buildings/summary", {
      buildingIds: ["507f1f77bcf86cd799439011"],
    });
    expect(
      mockGet.mock.calls.filter(([url]) => url === "/dashboard/config"),
    ).toHaveLength(configRequests);
    expect(
      mockGet.mock.calls.filter(([url]) => url === "/dashboard/buildings"),
    ).toHaveLength(buildingRequests);
  });

  it("uses newly fetched building IDs for a snapshot summary refresh", async () => {
    let responseBuildings: BuildingListItem[] = [];
    mockGet.mockImplementation((url: string) =>
      url === "/dashboard/buildings"
        ? Promise.resolve({ data: responseBuildings })
        : new Promise(() => {}),
    );
    renderPage(null, {
      dashboardUpdatedEventEnabled: true,
      featuresLoaded: true,
    });
    await waitFor(() =>
      expect(mockGet).toHaveBeenCalledWith("/dashboard/buildings"),
    );
    responseBuildings = [
      {
        id: "507f1f77bcf86cd799439011",
        name: { en: "New building", uk: "Новий будинок" },
        color: "blue",
        hasBoundStation: true,
        order: 1,
      },
    ];
    mockPost.mockClear();
    const handler = mockSubscribeEvents.mock.calls.at(-1)?.[0] as (
      event: EventItem,
    ) => void;

    handler({
      type: EventType.DashboardUpdated,
      data: { changed: ["buildings", "summary"] },
      private: false,
    });

    await waitFor(() =>
      expect(mockPost).toHaveBeenCalledWith("/dashboard/buildings/summary", {
        buildingIds: ["507f1f77bcf86cd799439011"],
      }),
    );
  });

  it("preserves unsaved dashboard edits when a snapshot update arrives", () => {
    const store = renderPage(
      { enable: true, regionId: 25, dsoId: 902, queue: "1.1" },
      { dashboardUpdatedEventEnabled: true, featuresLoaded: true },
      true,
    );
    const configRequests = mockGet.mock.calls.filter(
      ([url]) => url === "/dashboard/config",
    ).length;
    const buildingRequests = mockGet.mock.calls.filter(
      ([url]) => url === "/dashboard/buildings",
    ).length;
    const handler = mockSubscribeEvents.mock.calls.at(-1)?.[0] as (
      event: EventItem,
    ) => void;

    handler({
      type: EventType.DashboardUpdated,
      data: {},
      private: false,
    });

    expect(store.getState().dashboardConfig.changed).toBe(true);
    expect(store.getState().buildings.changed).toBe(true);
    expect(
      mockGet.mock.calls.filter(([url]) => url === "/dashboard/config"),
    ).toHaveLength(configRequests);
    expect(
      mockGet.mock.calls.filter(([url]) => url === "/dashboard/buildings"),
    ).toHaveLength(buildingRequests);
  });

  it("uses legacy dashboard events when backend snapshot mode is disabled", () => {
    renderPage(null, {
      dashboardUpdatedEventEnabled: false,
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

  it("refreshes from the API if snapshot update events stop arriving", () => {
    vi.useFakeTimers();
    try {
      renderPage(null, {
        dashboardUpdatedEventEnabled: true,
        featuresLoaded: true,
      });
      const configRequests = mockGet.mock.calls.filter(
        ([url]) => url === "/dashboard/config",
      ).length;

      act(() => {
        vi.advanceTimersByTime(5 * 60 * 1000);
      });

      expect(
        mockGet.mock.calls.filter(([url]) => url === "/dashboard/config"),
      ).toHaveLength(configRequests + 1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("preserves unsaved dashboard edits when the snapshot fallback timer fires", () => {
    vi.useFakeTimers();
    try {
      const store = renderPage(
        null,
        { dashboardUpdatedEventEnabled: true, featuresLoaded: true },
        true,
      );
      const configRequests = mockGet.mock.calls.filter(
        ([url]) => url === "/dashboard/config",
      ).length;
      const buildingRequests = mockGet.mock.calls.filter(
        ([url]) => url === "/dashboard/buildings",
      ).length;

      act(() => {
        vi.advanceTimersByTime(5 * 60 * 1000);
      });

      expect(store.getState().dashboardConfig.changed).toBe(true);
      expect(store.getState().buildings.changed).toBe(true);
      expect(
        mockGet.mock.calls.filter(([url]) => url === "/dashboard/config"),
      ).toHaveLength(configRequests);
      expect(
        mockGet.mock.calls.filter(([url]) => url === "/dashboard/buildings"),
      ).toHaveLength(buildingRequests);
    } finally {
      vi.useRealTimers();
    }
  });
});
