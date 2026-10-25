import { createAction, createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AppState {
  version: string;
  backendVersion: string;
}

const initialState: AppState = {
  version: "0000.00.00",
  backendVersion: "0000.00.00",
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
  },
});

export const appStarted = createAction("app/started");
export const { setVersion, setBackendVersion } = appSlice.actions;
export const appReducer = appSlice.reducer;