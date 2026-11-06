import { createAction, createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AppState {
  version: string;
  backendVersion: string;
  features: {
    dashboardUpdatedEventEnabled: boolean;
  };
  featuresLoaded: boolean;
}

const initialState: AppState = {
  version: "0000.00.00",
  backendVersion: "0000.00.00",
  features: {
    dashboardUpdatedEventEnabled: false,
  },
  featuresLoaded: false,
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
    setFeatures: (state, action: PayloadAction<AppState["features"]>) => {
      state.features = action.payload;
      state.featuresLoaded = true;
    },
    setFeaturesLoaded: (state) => {
      state.featuresLoaded = true;
    },
  },
});

export const appStarted = createAction("app/started");
export const { setVersion, setBackendVersion, setFeatures, setFeaturesLoaded } =
  appSlice.actions;
export const appReducer = appSlice.reducer;
