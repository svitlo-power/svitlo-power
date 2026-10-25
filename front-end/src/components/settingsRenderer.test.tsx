import { fireEvent, screen, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { renderWithStore } from "../test/storeTestUtils";
import SettingsRenderer from "./settingsRenderer";

const setting = {
  key: "test_setting",
  label: { en: "Test Setting", uk: "Тестове налаштування" },
  description: { en: "Test description", uk: "Опис тесту" },
  setting_type: "number" as const,
  default_value: 10,
  value: 10,
  editable: true,
  validation: { min: 0, max: 100 },
  category: {
    id: "test_category",
    label: { en: "Test Category", uk: "Тестова категорія" },
  },
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

  it("renders localized text inputs and saves all language values", async () => {
    const onChange = vi.fn().mockResolvedValue(undefined);
    renderWithStore(
      <SettingsRenderer
        setting={{
          ...setting,
          setting_type: "localizable_text",
          default_value: { en: "Default", uk: "За замовчуванням" },
          value: { en: "Dashboard", uk: "Панель" },
        }}
        onChange={onChange}
      />,
    );

    const inputs = screen.getAllByRole("textbox");
    expect(inputs).toHaveLength(2);
    expect(inputs[0]).toHaveValue("Dashboard");
    expect(inputs[1]).toHaveValue("Панель");

    fireEvent.change(inputs[0], { target: { value: "Updated" } });
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith("test_setting", {
        en: "Updated",
        uk: "Панель",
      });
    });
  });

  it("compares localized values by content when enabling reset", () => {
    renderWithStore(
      <SettingsRenderer
        setting={{
          ...setting,
          setting_type: "localizable_text",
          default_value: { en: "Dashboard", uk: "Панель" },
          value: { en: "Dashboard", uk: "Панель" },
        }}
        resettable
      />,
    );

    expect(screen.getByRole("button", { name: "Reset to Defaults" })).toBeDisabled();
  });

  it("disables the rendered control when requested", () => {
    renderWithStore(<SettingsRenderer setting={setting} disabled />);
    expect(screen.getByRole("textbox", { name: "Test Setting" })).toBeDisabled();
  });

  it("disables a setting marked read-only and hides its reset action", () => {
    const onChange = vi.fn();
    const onReset = vi.fn();
    renderWithStore(
      <SettingsRenderer
        setting={{ ...setting, editable: false, value: 20 }}
        onChange={onChange}
        onReset={onReset}
        resettable
      />,
    );

    expect(screen.getByRole("textbox", { name: "Test Setting" })).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Reset to Defaults" })).not.toBeInTheDocument();
  });

  it("shows a legacy name stored in a read-only numeric setting until it is resolved", () => {
    renderWithStore(
      <SettingsRenderer
        setting={{ ...setting, editable: false, value: "Kyiv" }}
      />,
    );

    expect(screen.getByRole("textbox", { name: "Test Setting" })).toHaveValue("Kyiv");
    expect(screen.getByRole("textbox", { name: "Test Setting" })).toBeDisabled();
  });

  it("resets a non-default value through the supplied reset handler", async () => {
    const onReset = vi.fn().mockResolvedValue(undefined);
    renderWithStore(
      <SettingsRenderer
        setting={{ ...setting, value: 20 }}
        onReset={onReset}
        resettable
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Reset to Defaults" }));

    await waitFor(() => expect(onReset).toHaveBeenCalledWith("test_setting"));
    expect(screen.getByRole("textbox", { name: "Test Setting" })).toHaveValue("10");
  });

  it("disables reset when the value already matches the default", () => {
    renderWithStore(<SettingsRenderer setting={setting} resettable />);
    expect(screen.getByRole("button", { name: "Reset to Defaults" })).toBeDisabled();
  });
});
