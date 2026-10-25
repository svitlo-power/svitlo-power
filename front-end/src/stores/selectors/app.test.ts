import { selectAppVersion, selectBackendVersion } from "./app";

describe("app selectors", () => {
  const mockState = {
    app: {
      version: "2026.10.01",
      backendVersion: "2026.10.02",
    },
  } as any;

  it("should select app version from state", () => {
    const result = selectAppVersion(mockState);
    expect(result).toBe("2026.10.01");
  });

  it("should return default version when not set", () => {
    const stateWithoutVersion = {
      app: {
        version: "0000.00.00",
        backendVersion: "0000.00.00",
      },
    } as any;

    const result = selectAppVersion(stateWithoutVersion);
    expect(result).toBe("0000.00.00");
  });

  it("should select the backend version", () => {
    const state = {
      app: { version: "2026.10.01", backendVersion: "2026.10.02" },
    } as any;

    expect(selectBackendVersion(state)).toBe("2026.10.02");
  });
});