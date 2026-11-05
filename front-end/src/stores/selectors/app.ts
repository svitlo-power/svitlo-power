import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectApp = (state: RootState) => state.app;

export const selectAppVersion = createSelector(
  [selectApp],
  (app) => app.version,
);
export const selectBackendVersion = createSelector(
  [selectApp],
  (app) => app.backendVersion,
);
export const selectBackendRedisDashboardEnabled = createSelector(
  [selectApp],
  (app) => app.backendRedisDashboardEnabled,
);
export const selectBackendFeaturesLoaded = createSelector(
  [selectApp],
  (app) => app.backendFeaturesLoaded,
);
