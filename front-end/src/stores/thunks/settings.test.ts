import { vi } from "vitest";
import { waitFor } from "@testing-library/react";
import { createTestStore } from "../../test/storeTestUtils";
import { cancelSettingsEditing, fetchSettings, saveSettings } from "./settings";

const { mockGet, mockPost, mockPut } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockPut: vi.fn(),
}));

vi.mock("../../utils/apiClient", () => ({
  default: { get: mockGet, post: mockPost, put: mockPut },
}));

const serverSetting = {
  key: "discharge",
  label: { en: "Discharge", uk: "Розрядження" },
  description: { en: "Battery target", uk: "Ціль батареї" },
  setting_type: "number" as const,
  default_value: 10,
  value: 10,
  validation: { min: 0, max: 100 },
  category_id: "power",
  created_at: "2024-01-01T00:00:00.000Z",
  updated_at: "2024-01-01T00:00:00.000Z",
};

const fetchResponse = (items = [serverSetting]) => ({
  data: {
    categories: {
      power: {
        id: "power",
        label: { en: "Power", uk: "Потужність" },
        settings: items,
      },
    },
  },
});

const settingWithCategory = {
  ...serverSetting,
  category: { id: "power", label: { en: "Power", uk: "Потужність" } },
};
const fetchedServerSetting = Object.fromEntries(
  Object.entries(serverSetting).filter(([key]) => key !== "category_id"),
);

describe("settings thunks", () => {
  beforeEach(() => vi.clearAllMocks());

  it("flattens fetched categories and initializes client-only flags", async () => {
    mockGet.mockResolvedValue(fetchResponse());
    const store = createTestStore();

    await expect(store.dispatch(fetchSettings()).unwrap()).resolves.toEqual([
      {
        ...fetchedServerSetting,
        category: { id: "power", label: { en: "Power", uk: "Потужність" } },
      },
    ]);

    expect(mockGet).toHaveBeenCalledWith("/settings");
    expect(store.getState().settings.items).toEqual([{
      ...fetchedServerSetting,
      category: { id: "power", label: { en: "Power", uk: "Потужність" } },
      changed: false,
      created: false,
    }]);
  });

  it("keeps the server error when fetching fails", async () => {
    mockGet.mockRejectedValue(new Error("Network error"));
    const store = createTestStore();

    await expect(store.dispatch(fetchSettings()).unwrap()).rejects.toBe("Network error");
    expect(store.getState().settings.error).toBe("Network error");
  });

  it("saves changed existing settings with PUT, then refreshes them", async () => {
    const changedSetting = { ...settingWithCategory, value: 20, changed: true, created: false };
    mockPut.mockResolvedValue({ data: changedSetting });
    mockGet.mockResolvedValue(fetchResponse([{ ...serverSetting, value: 20 }]));
    const store = createTestStore({
      settings: { items: [changedSetting], loading: false, creating: false, changed: true, error: null },
    });

    await store.dispatch(saveSettings()).unwrap();

    expect(mockPut).toHaveBeenCalledWith("/settings/discharge", expect.objectContaining({ value: 20 }));
    await waitFor(() => expect(store.getState().settings.items[0]).toEqual({
      ...fetchedServerSetting,
      category: { id: "power", label: { en: "Power", uk: "Потужність" } },
      value: 20,
      changed: false,
      created: false,
    }));
  });

  it("uses POST for newly-created settings", async () => {
    const createdSetting = { ...settingWithCategory, key: "new-setting", changed: true, created: true };
    mockPost.mockResolvedValue({ data: createdSetting });
    mockGet.mockResolvedValue(fetchResponse([createdSetting]));
    const store = createTestStore({
      settings: { items: [createdSetting], loading: false, creating: false, changed: true, error: null },
    });

    await store.dispatch(saveSettings()).unwrap();

    expect(mockPost).toHaveBeenCalledWith("/settings", expect.objectContaining({ key: "new-setting" }));
  });

  it("refreshes settings when editing is cancelled", async () => {
    mockGet.mockResolvedValue(fetchResponse());
    const store = createTestStore({
      settings: { items: [], loading: false, creating: true, changed: true, error: null },
    });

    await store.dispatch(cancelSettingsEditing()).unwrap();

    await waitFor(() => expect(store.getState().settings.items).toHaveLength(1));
    expect(store.getState().settings.creating).toBe(false);
  });
});
