import { vi } from "vitest";
import { createTestStore } from "../../test/storeTestUtils";
import { saveStations } from "./stations";

const { mockPut, mockPost } = vi.hoisted(() => ({
  mockPut: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock("../../utils/apiClient", () => ({
  default: { put: mockPut, post: mockPost },
}));

const station = {
  id: "station-1" as const,
  stationName: "Test Station",
  stationAlias: { en: "TS", uk: "ТС" },
  connectionStatus: "online",
  gridInterconnectionType: "grid",
  lastUpdateTime: new Date(),
  connectionName: null,
  batteryCapacity: 10,
  dischargeTargetSoc: 30,
  chargeTargetSoc: 80,
  enabled: true,
  order: 1,
  changed: true,
};

describe("stations thunks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("saves station SOC overrides with PUT", async () => {
    mockPut.mockResolvedValue({ data: { id: "station-1" } });
    const store = createTestStore({
      stations: { stations: [station], loading: false, error: null },
    });

    await store.dispatch(saveStations()).unwrap();

    expect(mockPut).toHaveBeenCalledWith("/stations/save", {
      id: "station-1",
      enabled: true,
      order: 1,
      batteryCapacity: 10,
      alias: { en: "TS", uk: "ТС" },
      dischargeTargetSoc: 30,
      chargeTargetSoc: 80,
    });
  });

  it("does not save unchanged stations", async () => {
    mockPut.mockResolvedValue({ data: { id: "station-1" } });
    const store = createTestStore({
      stations: { stations: [{ ...station, changed: false }], loading: false, error: null },
    });

    await store.dispatch(saveStations()).unwrap();

    expect(mockPut).not.toHaveBeenCalled();
  });
});
