import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useCallback, useState } from "react";
import { TFunction } from "i18next";
import { vi } from "vitest";
import { OutagesScheduleConfig } from "../../../schemas/dashboardEdit";
import { OutagesScheduleSelection } from "./outagesScheduleSelection";

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock("../../../utils/apiClient", () => ({
  default: { get: mockGet },
}));

const translate = ((key: string, options?: Record<string, string>) => {
  if (key === "dashboardEdit.selectionSummary") {
    return `${options?.region} · ${options?.provider} · Queue ${options?.queue}`;
  }
  return ({
    "dashboardEdit.region": "Region",
    "dashboardEdit.selectRegion": "Select a region",
    "dashboardEdit.provider": "Provider",
    "dashboardEdit.selectProvider": "Select a provider",
    "dashboardEdit.queue": "Queue",
    "dashboardEdit.selectQueue": "Select a queue",
    "dashboardEdit.loading": "Loading...",
    "button.back": "Back",
    "button.next": "Next",
    "dashboardEdit.discoveryError": "Unable to load options.",
  }[key] ?? key);
}) as TFunction;

const Harness = ({ initialValue }: { initialValue: OutagesScheduleConfig }) => {
  const [value, setValue] = useState(initialValue);
  const handleChange = useCallback((changes: Partial<OutagesScheduleConfig>) => {
    setValue((current) => ({ ...current, ...changes }));
  }, []);

  return (
    <MantineProvider>
      <OutagesScheduleSelection value={value} t={translate} onChange={handleChange} />
    </MantineProvider>
  );
};

describe("OutagesScheduleSelection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as typeof ResizeObserver;
    mockGet.mockImplementation((url: string) => {
      if (url === "/outagesSchedule/regions") {
        return Promise.resolve({
          data: [{ id: 25, value: "Київ", label: "Київ" }],
        });
      }
      if (url === "/outagesSchedule/providers/%D0%9A%D0%B8%D1%97%D0%B2") {
        return Promise.resolve({ data: [{ id: 902, name: "ДТЕК" }] });
      }
      if (url === "/outagesSchedule/queues/25/902") {
        return Promise.resolve({ data: ["1.1", "1.2"] });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });
  });

  it("loads and walks through region, provider, and queue selections", async () => {
    const user = userEvent.setup();
    render(<Harness initialValue={{ enable: true, region: null, dso: null, queue: null }} />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/outagesSchedule/regions"));
    await user.click(screen.getByRole("combobox", { name: "Region" }));
    fireEvent.click(screen.getByRole("option", { name: "Київ", hidden: true }));

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith(
      "/outagesSchedule/providers/%D0%9A%D0%B8%D1%97%D0%B2",
    ));
    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/outagesSchedule/queues/25/902"));

    expect(await screen.findByRole("combobox", { name: "Queue" })).toBeInTheDocument();
    await user.click(screen.getByRole("combobox", { name: "Queue" }));
    fireEvent.click(screen.getByText("1.2"));

    expect(screen.getByText("Київ · ДТЕК · Queue 1.2")).toBeInTheDocument();
  });

  it("shows a loader instead of the empty initial step while loading regions", async () => {
    let resolveRegions: (value: { data: { id: number; value: string; label: string }[] }) => void;
    mockGet.mockReturnValueOnce(new Promise((resolve) => {
      resolveRegions = resolve;
    }));
    render(<Harness initialValue={{ enable: true, region: null, dso: null, queue: null }} />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.queryByRole("combobox", { name: "Region" })).not.toBeInTheDocument();

    resolveRegions!({ data: [{ id: 25, value: "Київ", label: "Київ" }] });
    expect(await screen.findByRole("combobox", { name: "Region" })).toBeInTheDocument();
  });

  it("supports navigating back to the previous step", async () => {
    const user = userEvent.setup();
    render(<Harness initialValue={{ enable: true, region: null, dso: null, queue: null }} />);

    await waitFor(() => expect(mockGet).toHaveBeenCalledWith("/outagesSchedule/regions"));
    await user.click(screen.getByRole("combobox", { name: "Region" }));
    fireEvent.click(screen.getByRole("option", { name: "Київ", hidden: true }));
    await screen.findByRole("combobox", { name: "Provider" });

    await user.click(screen.getByRole("button", { name: "Back" }));
    await user.click(screen.getByRole("button", { name: "Back" }));
    expect(screen.getByRole("combobox", { name: "Region" })).toBeInTheDocument();
  });

  it("shows an error when region discovery fails", async () => {
    mockGet.mockRejectedValueOnce(new Error("YASNO unavailable"));
    render(<Harness initialValue={{ enable: true, region: null, dso: null, queue: null }} />);

    expect(await screen.findByText("YASNO unavailable")).toBeInTheDocument();
  });
});
