import { screen } from "@testing-library/react";
import { vi } from "vitest";
import { renderWithStore } from "../../../test/storeTestUtils";
import { SocCell } from "./socCell";

const defaultProps = {
  t: ((key: string, opts?: any) => {
    const messages: Record<string, string> = {
      "socEdit.dischargeShort": "Discharge",
      "socEdit.chargeShort": "Charge",
      "socEdit.useSetting": "Use setting",
      "socEdit.tooltip": "Edit target SOC overrides",
    };
    let msg = messages[key] || key;
    if (opts?.value !== undefined) {
      msg = msg.replace("{{value}}", String(opts.value));
    }
    return msg;
  }) as any,
  id: "station-1",
  dischargeTargetSoc: null,
  chargeTargetSoc: null,
  defaultDischargeTargetSoc: 10,
  defaultChargeTargetSoc: 97,
  onSocChange: vi.fn(),
};

describe("SocCell", () => {
  it("shows default values when station overrides are null", () => {
    renderWithStore(<SocCell {...defaultProps} />);

    expect(screen.getByText("Discharge: 10%")).toBeInTheDocument();
    expect(screen.getByText("Charge: 97%")).toBeInTheDocument();
  });

  it("shows station override values when set", () => {
    renderWithStore(<SocCell {...defaultProps} dischargeTargetSoc={30} chargeTargetSoc={80} />);

    expect(screen.getByText("Discharge: 30%")).toBeInTheDocument();
    expect(screen.getByText("Charge: 80%")).toBeInTheDocument();
  });

  it("greys out values that come from the setting", () => {
    const { rerender } = renderWithStore(<SocCell {...defaultProps} />);

    const dischargeText = screen.getByText("Discharge: 10%");
    const chargeText = screen.getByText("Charge: 97%");
    expect(dischargeText).toHaveStyle({ color: "var(--mantine-color-dimmed)" });
    expect(chargeText).toHaveStyle({ color: "var(--mantine-color-dimmed)" });

    rerender(<SocCell {...defaultProps} dischargeTargetSoc={30} chargeTargetSoc={80} />);

    expect(screen.getByText("Discharge: 30%")).not.toHaveStyle({ color: "var(--mantine-color-dimmed)" });
    expect(screen.getByText("Charge: 80%")).not.toHaveStyle({ color: "var(--mantine-color-dimmed)" });
  });
});
