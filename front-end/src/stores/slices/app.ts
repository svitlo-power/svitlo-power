import { createAction, createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AppState {
  version: string;
  backendVersion: string;
  backendRedisDashboardEnabled: boolean;
  backendFeaturesLoaded: boolean;
}

const initialState: AppState = {
  version: "0000.00.00",
  backendVersion: "0000.00.00",
  backendRedisDashboardEnabled: false,
  backendFeaturesLoaded: false,
};

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setVersion: (state, action: PayloadAction<string>) => {
      state.version = action.payload;
    },
    setBackendVersion: (state, action: PayloadAction<string>) => {
      state.backendVersion = action.payload;
    },
    setBackendRedisDashboardEnabled: (
      state,
      action: PayloadAction<boolean>,
    ) => {
      state.backendRedisDashboardEnabled = action.payload;
      state.backendFeaturesLoaded = true;
    },
    setBackendFeaturesLoaded: (state) => {
      state.backendFeaturesLoaded = true;
    },
  },
});

export const appStarted = createAction("app/started");
export const {
  setVersion,
  setBackendVersion,
  setBackendRedisDashboardEnabled,
  setBackendFeaturesLoaded,
} = appSlice.actions;
export const appReducer = appSlice.reducer;
