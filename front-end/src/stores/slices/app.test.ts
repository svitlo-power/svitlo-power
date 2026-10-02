import { appReducer, setVersion } from "./app";

describe("app slice", () => {
  const initialState = { version: "0000.00.00" };

  it("should return initial state", () => {
    expect(appReducer(undefined, { type: "unknown" })).toEqual(initialState);
  });

  it("should set version", () => {
    const newVersion = "2026.10.01";
    const action = setVersion(newVersion);
    const state = appReducer(initialState, action);
    expect(state.version).toBe(newVersion);
  });

  it("should handle multiple version updates", () => {
    let state = appReducer(initialState, setVersion("2026.10.01"));
    expect(state.version).toBe("2026.10.01");

    state = appReducer(state, setVersion("2026.10.02"));
    expect(state.version).toBe("2026.10.02");
  });
});