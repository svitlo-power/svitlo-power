import { logout, setFeatures } from "./slices";
import { rootReducer } from "./rootReducer";

describe("rootReducer", () => {
  it("preserves app features when logging out", () => {
    const state = rootReducer(
      undefined,
      setFeatures({ dashboardUpdatedEventEnabled: true }),
    );

    const nextState = rootReducer(state, logout());

    expect(nextState.app.features.dashboardUpdatedEventEnabled).toBe(true);
    expect(nextState.app.featuresLoaded).toBe(true);
    expect(nextState.auth.accessToken).toBeNull();
  });
});
