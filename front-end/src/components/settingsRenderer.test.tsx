import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { renderWithStore } from "../test/storeTestUtils";
import SettingsRenderer from "./settingsRenderer";

const setting = {
  key: "test_setting",
  label: "Test Setting",
  description: "Test description",
  setting_type: "number" as const,
  default_value: 10,
  value: 10,
  validation: { min: 0, max: 100 },
  category: "test_category",
};

describe("SettingsRenderer", () => {
  it("renders the number setting with its label and description", () => {
    renderWithStore(<SettingsRenderer setting={setting} />);

    expect(screen.getByRole("textbox", { name: "Test Setting" })).toHaveValue("10");
    expect(screen.getByText("Test description")).toBeInTheDocument();
  });

  it("reports number validation errors without saving", async () => {
    const onChange = vi.fn();
    renderWithStore(<SettingsRenderer setting={setting} onChange={onChange} />);

    fireEvent.change(screen.getByRole("textbox", { name: "Test Setting" }), { target: { value: "101" } });

    expect(await screen.findByText("Value must be at most 100")).toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it("passes valid values to the supplied change handler", async () => {
    const onChange = vi.fn().mockResolvedValue(undefined);
    renderWithStore(<SettingsRenderer setting={setting} onChange={onChange} />);

    fireEvent.change(screen.getByRole("textbox", { name: "Test Setting" }), { target: { value: "20" } });

    await waitFor(() => expect(onChange).toHaveBeenCalledWith("test_setting", 20));
  });

  it("renders the appropriate Mantine controls for other setting types", () => {
    const { rerender } = renderWithStore(
      <SettingsRenderer setting={{ ...setting, setting_type: "text", value: "hello", default_value: "hello" }} />
    );
    expect(screen.getByRole("textbox", { name: "Test Setting" })).toHaveValue("hello");

    rerender(<SettingsRenderer setting={{ ...setting, setting_type: "boolean", value: true, default_value: true }} />);
    expect(screen.getByRole("switch", { name: /Test Setting/ })).toBeChecked();

    // Mantine Select observes its dropdown size; use a constructible browser stub.
    global.ResizeObserver = class {
      observe() {}
      unobserve() {}
      disconnect() {}
    } as typeof ResizeObserver;
    rerender(
      <SettingsRenderer setting={{
        ...setting,
        setting_type: "select",
        value: "one",
        default_value: "one",
        validation: { options: [{ value: "one", label: "One" }] },
      }} />
    );
    expect(screen.getByRole("combobox", { name: "Test Setting" })).toHaveValue("One");
  });

  it("disables the rendered control when requested", () => {
    renderWithStore(<SettingsRenderer setting={setting} disabled />);
    expect(screen.getByRole("textbox", { name: "Test Setting" })).toBeDisabled();
  });
});
