import { appReducer, setFeatures, setBackendVersion, setVersion } from "./app";

describe("app slice", () => {
  const initialState = {
    version: "0000.00.00",
    backendVersion: "0000.00.00",
    features: {
      backendRedisDashboardEnabled: false,
    },
    featuresLoaded: false,
  };

  it("should return initial state", () => {
    expect(appReducer(undefined, { type: "unknown" })).toEqual(initialState);
  });

  it("should set version", () => {
    const newVersion = "2026.10.01";
    const action = setVersion(newVersion);
    const state = appReducer(initialState, action);
    expect(state.version).toBe(newVersion);
  });

  it("should set backend version", () => {
    const state = appReducer(initialState, setBackendVersion("2026.10.02"));
    expect(state.backendVersion).toBe("2026.10.02");
  });

  it("should store features and mark them loaded", () => {
    const features = { backendRedisDashboardEnabled: true };
    const state = appReducer(initialState, setFeatures(features));
    expect(state.features).toEqual(features);
    expect(state.featuresLoaded).toBe(true);
  });

  it("should handle multiple version updates", () => {
    let state = appReducer(initialState, setVersion("2026.10.01"));
    expect(state.version).toBe("2026.10.01");

    state = appReducer(state, setVersion("2026.10.02"));
    expect(state.version).toBe("2026.10.02");
  });
});
