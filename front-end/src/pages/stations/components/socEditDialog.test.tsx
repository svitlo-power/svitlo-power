import { screen, fireEvent, waitFor } from "@testing-library/react";
import { vi } from "vitest";
import { renderWithStore } from "../../../test/storeTestUtils";
import { openSocEditDialog } from "./socEditDialog";
import type { ReactNode } from "react";

const mockOpen = vi.hoisted(() => vi.fn());

vi.mock("@mantine/modals", () => ({
  modals: {
    open: mockOpen,
    close: vi.fn(),
  },
}));

const defaultProps = {
  t: ((key: string, opts?: any) => {
    const messages: Record<string, string> = {
      "socEdit.title": "Edit target SOC",
      "socEdit.dischargeLabel": "Discharge Target SOC (%)",
      "socEdit.chargeLabel": "Charge Target SOC (%)",
      "socEdit.useSetting": "Use setting ({{value}}%)",
      "button.cancel": "Cancel",
      "button.save": "Save",
    };
    let msg = messages[key] || key;
    if (opts?.value !== undefined) {
      msg = msg.replace("{{value}}", String(opts.value));
    }
    return msg;
  }) as any,
  dischargeTargetSoc: null,
  chargeTargetSoc: null,
  defaultDischargeTargetSoc: 10,
  defaultChargeTargetSoc: 97,
  onClose: vi.fn(),
};

let capturedChildren: React.ReactNode;

beforeEach(() => {
  vi.clearAllMocks();
  mockOpen.mockImplementation(({ children }: { children: React.ReactNode }) => {
    capturedChildren = children;
    return "modal-id";
  });
});

const renderDialog = (props = defaultProps) => {
  openSocEditDialog(props);
  return renderWithStore(capturedChildren as React.ReactElement);
};

describe("openSocEditDialog", () => {
  it("shows default values when station overrides are null", () => {
    renderDialog();

    expect(screen.getByLabelText("Discharge Target SOC (%)")).toHaveValue("");
    expect(screen.getByLabelText("Charge Target SOC (%)")).toHaveValue("");
  });

  it("shows station override values when set", () => {
    renderDialog({ ...defaultProps, dischargeTargetSoc: 30, chargeTargetSoc: 80 });

    expect(screen.getByLabelText("Discharge Target SOC (%)")).toHaveValue("30");
    expect(screen.getByLabelText("Charge Target SOC (%)")).toHaveValue("80");
  });

  it("greys out inputs when station override is null (uses setting)", () => {
    renderDialog();

    const dischargeInput = screen.getByLabelText("Discharge Target SOC (%)");
    const chargeInput = screen.getByLabelText("Charge Target SOC (%)");
    expect(dischargeInput.closest(".mantine-InputWrapper-root")).toHaveStyle(
      "opacity: 0.5"
    );
    expect(chargeInput.closest(".mantine-InputWrapper-root")).toHaveStyle(
      "opacity: 0.5"
    );
  });

  it("enables inputs when station override is set", () => {
    renderDialog({ ...defaultProps, dischargeTargetSoc: 30, chargeTargetSoc: 80 });

    expect(screen.getByLabelText("Discharge Target SOC (%)")).not.toBeDisabled();
    expect(screen.getByLabelText("Charge Target SOC (%)")).not.toBeDisabled();
  });

  it("calls onClose with new values on save", async () => {
    const onClose = vi.fn();
    renderDialog({ ...defaultProps, onClose });

    fireEvent.change(screen.getByLabelText("Discharge Target SOC (%)"), {
      target: { value: "40" },
    });
    fireEvent.change(screen.getByLabelText("Charge Target SOC (%)"), {
      target: { value: "85" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => expect(onClose).toHaveBeenCalledWith(true, 40, 85));
  });

  it("calls onClose with false on cancel", () => {
    const onClose = vi.fn();
    renderDialog({ ...defaultProps, onClose });

    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledWith(false, null, null);
  });

  it("shows use setting hint when input is disabled", () => {
    renderDialog();

    expect(screen.getByLabelText("Discharge Target SOC (%)")).toHaveAttribute(
      "placeholder",
      "Use setting (10%)"
    );
    expect(screen.getByLabelText("Charge Target SOC (%)")).toHaveAttribute(
      "placeholder",
      "Use setting (97%)"
    );
  });
});

