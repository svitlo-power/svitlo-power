import { screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { vi } from "vitest";
import { PageHeaderContentProvider } from "../../providers";
import { createTestStore, renderWithStore } from "../../test/storeTestUtils";
import { SystemSettingsPage } from "./systemSettings";

const { mockGet } = vi.hoisted(() => ({ mockGet: vi.fn() }));

vi.mock("../../utils/apiClient", () => ({
  default: { get: mockGet, post: vi.fn(), put: vi.fn() },
}));

vi.mock("../../components/page", () => ({
  Page: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

const setting = {
  key: "discharge",
  label: "Discharge target",
  description: "Battery target",
  setting_type: "number" as const,
  default_value: 10,
  value: 10,
  category: "power_estimation",
  created_at: "2024-01-01T00:00:00.000Z",
  updated_at: "2024-01-01T00:00:00.000Z",
  changed: false,
  created: false,
};

const renderPage = (items = [setting], error: string | null = null, fetchFailure = false) => {
  if (fetchFailure) {
    mockGet.mockRejectedValue(new Error(error));
  } else {
    mockGet.mockResolvedValue({ data: { categories: { power_estimation: items } } });
  }
  const store = createTestStore({
    settings: { items, loading: false, creating: false, changed: false, error },
  });
  return renderWithStore(
    <PageHeaderContentProvider><SystemSettingsPage /></PageHeaderContentProvider>,
    { store },
  );
};

describe("SystemSettingsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders settings within their category", () => {
    renderPage();

    expect(screen.getByText("Power Estimation")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Discharge target" })).toHaveValue("10");
  });

  it("shows the empty-state message when no settings exist", () => {
    renderPage([]);
    expect(screen.getByText("No settings available")).toBeInTheDocument();
  });

  it("shows a settings error", async () => {
    renderPage([], "Unable to load settings", true);
    expect(await screen.findByText("Unable to load settings")).toBeInTheDocument();
  });

  it("fetches settings when mounted", async () => {
    renderPage();
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/settings"));
  });
});
