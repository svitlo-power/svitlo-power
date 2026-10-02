import { selectAppVersion } from "./app";

describe("app selectors", () => {
  const mockState = {
    app: {
      version: "2026.10.01",
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
      },
    } as any;

    const result = selectAppVersion(stateWithoutVersion);
    expect(result).toBe("0000.00.00");
  });
});