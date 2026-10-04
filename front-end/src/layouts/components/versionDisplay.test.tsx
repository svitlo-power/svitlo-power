import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import { describe, expect, it } from "vitest";
import { VersionDisplay } from "./versionDisplay";
import { Provider } from "react-redux";
import { MantineProvider } from "@mantine/core";
import { store } from "../../stores/store";

const renderWithProviders = () => {
  return render(
    <Provider store={store}>
      <MantineProvider>
        <VersionDisplay />
      </MantineProvider>
    </Provider>
  );
};

describe("VersionDisplay", () => {
  it("renders version from store", () => {
    renderWithProviders();
    // The default version is "0000.00.00"
    expect(screen.getByTestId("navbar-version-label")).toHaveTextContent("v0000.00.00");
  });

  it("renders version with v prefix", () => {
    renderWithProviders();
    const versionElement = screen.getByTestId("navbar-version-label");
    expect(versionElement.textContent).toMatch(/^v\d{4}\.\d{2}\.\d{2}$/);
  });

  it("renders version in compact mode", () => {
    render(
      <Provider store={store}>
        <MantineProvider>
          <VersionDisplay compact />
        </MantineProvider>
      </Provider>
    );

    expect(screen.getByTestId("navbar-version-label")).toHaveTextContent("v0000.00.00");
  });
});