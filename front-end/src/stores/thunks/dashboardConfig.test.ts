import { vi } from "vitest";
import { createTestStore } from "../../test/storeTestUtils";
import { fetchDashboardConfig, saveDashboardConfig } from "./dashboardConfig";

const { mockGet, mockPut } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPut: vi.fn(),
}));

vi.mock("../../utils/apiClient", () => ({
  default: { get: mockGet, put: mockPut },
}));

describe("dashboard config thunks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("normalizes legacy enabled settings to the nested response format", async () => {
    mockGet.mockResolvedValue({
      data: {
        title: { en: "Dashboard", uk: "Панель" },
        enableOutagesSchedule: true,
        outagesScheduleQueue: "1.1",
      },
    });
    const store = createTestStore();

    await expect(store.dispatch(fetchDashboardConfig()).unwrap()).resolves.toEqual({
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: {
        enable: true,
        region: "Kyiv",
        dso: "Yasno",
        queue: "1.1",
      },
    });
    expect(mockGet).toHaveBeenCalledWith("/dashboard/config");
  });

  it("preserves disabled nested settings as null", async () => {
    mockGet.mockResolvedValue({
      data: {
        title: { en: "Dashboard", uk: "Панель" },
        outagesSchedule: {
          enable: false,
          region: null,
          dso: null,
          queue: null,
        },
      },
    });
    const store = createTestStore();

    await expect(store.dispatch(fetchDashboardConfig()).unwrap()).resolves.toEqual({
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: null,
    });
  });

  it("saves nested config and refreshes it from the server", async () => {
    const config = {
      title: { en: "Dashboard", uk: "Панель" },
      outagesSchedule: {
        enable: true,
        region: "Київ",
        dso: "ДТЕК",
        queue: "1.1",
      },
    };
    mockPut.mockResolvedValue({ data: config });
    mockGet.mockResolvedValue({ data: config });
    const store = createTestStore({
      dashboardConfig: {
        config,
        loading: false,
        error: null,
        changed: true,
      },
    });

    await store.dispatch(saveDashboardConfig()).unwrap();

    expect(mockPut).toHaveBeenCalledWith("/dashboard/config", config);
    expect(mockGet).toHaveBeenCalledWith("/dashboard/config");
  });

  it("returns the API error when fetching configuration fails", async () => {
    mockGet.mockRejectedValue(new Error("Network error"));
    const store = createTestStore();

    await expect(store.dispatch(fetchDashboardConfig()).unwrap()).rejects.toBe("Network error");
    expect(store.getState().dashboardConfig.error).toBe("Network error");
  });
});
