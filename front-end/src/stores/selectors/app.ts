import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectApp = (state: RootState) => state.app;

export const selectAppVersion = createSelector([selectApp], (app) => app.version);
export const selectBackendVersion = createSelector([selectApp], (app) => app.backendVersion);