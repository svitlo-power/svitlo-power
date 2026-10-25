import { screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { vi } from "vitest";
import { PageHeaderContentProvider, useHeaderContent } from "../../providers";
import { createTestStore, renderWithStore } from "../../test/storeTestUtils";
import { SystemSettingsPage } from "./systemSettings";

const { mockGet, translate, mockLanguage } = vi.hoisted(() => {
  const translations: Record<string, string> = {
    "settings.noSettings": "No settings available",
    "button.save": "Save",
    "button.cancel": "Cancel",
  };
  return {
    mockGet: vi.fn(),
    translate: (key: string) => translations[key] || key,
    mockLanguage: { current: "en" },
  };
});

vi.mock("../../utils/apiClient", () => ({
  default: { get: mockGet, post: vi.fn(), put: vi.fn() },
}));

vi.mock("../../components/page", () => ({
  Page: ({ children }: { children: ReactNode }) => <>{children}</>,
}));

vi.mock("react-i18next", async () => {
  const actual = await vi.importActual("react-i18next");
  return {
    ...actual,
    useTranslation: () => ({
      t: translate,
      i18n: {
        language: mockLanguage.current,
        resolvedLanguage: mockLanguage.current,
      },
    }),
  };
});

const HeaderButtons = () => {
  const { headerButtons } = useHeaderContent();
  return <>{headerButtons.map((button) => <button key={button.text} onClick={button.onClick}>{button.text}</button>)}</>;
};

const setting = {
  key: "discharge",
  label: { en: "Discharge target", uk: "Ціль розрядження" },
  description: { en: "Battery target", uk: "Ціль батареї" },
  setting_type: "number" as const,
  default_value: 10,
  value: 10,
  editable: true,
  category_id: "category-id",
  created_at: "2024-01-01T00:00:00.000Z",
  updated_at: "2024-01-01T00:00:00.000Z",
  changed: false,
  created: false,
};

const renderPage = (items = [setting], error: string | null = null, fetchFailure = false) => {
  if (fetchFailure) {
    mockGet.mockRejectedValue(new Error(error));
  } else {
    mockGet.mockResolvedValue({
      data: {
        categories: {
          "category-id": {
            id: "category-id",
            label: { en: "Power Estimation", uk: "Оцінка потужності" },
            settings: items,
          },
        },
      },
    });
  }
  const store = createTestStore({
    settings: {
      items: items.map((item) => ({
        ...item,
        category: {
          id: item.category_id,
          label: { en: "Power Estimation", uk: "Оцінка потужності" },
        },
      })),
      loading: false,
      creating: false,
      changed: false,
      error,
    },
  });
  return renderWithStore(
    <PageHeaderContentProvider>
      <SystemSettingsPage />
      <HeaderButtons />
    </PageHeaderContentProvider>,
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

  it("renders localized category and setting metadata", () => {
    mockLanguage.current = "uk";
    renderPage();

    expect(screen.getByText("Оцінка потужності")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Ціль розрядження" })).toHaveValue("10");
    expect(screen.getByText("Ціль батареї")).toBeInTheDocument();
    mockLanguage.current = "en";
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

  it("does not show reset-to-default controls", async () => {
    renderPage();

    expect(await screen.findByRole("textbox", { name: "Discharge target" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reset to Defaults" })).not.toBeInTheDocument();
  });
});
