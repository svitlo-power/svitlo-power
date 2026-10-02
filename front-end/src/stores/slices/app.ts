import { createAction, createSlice, PayloadAction } from "@reduxjs/toolkit";

interface AppState {
  version: string;
}

const initialState: AppState = {
  version: "0000.00.00",
};

const appSlice = createSlice({
  name: "app",
  initialState,
  reducers: {
    setVersion: (state, action: PayloadAction<string>) => {
      state.version = action.payload;
    },
  },
});

export const appStarted = createAction("app/started");
export const { setVersion } = appSlice.actions;
export const appReducer = appSlice.reducer;