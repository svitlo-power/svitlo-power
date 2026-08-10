import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { LoginHistoryItem, LoginHistoryState } from "../types";
import { fetchLoginHistory } from "../thunks";

const initialState: LoginHistoryState = {
  items: [],
  loading: false,
  error: null,
};

export const loginHistorySlice = createSlice({
  name: 'loginHistory',
  initialState: initialState,
  reducers: {
    clearLoginHistory(state) {
      state.items = [];
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchLoginHistory.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchLoginHistory.fulfilled, (state, { payload }: PayloadAction<LoginHistoryItem[]>) => {
        state.items = payload;
        state.loading = false;
      })
      .addCase(fetchLoginHistory.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

export const { clearLoginHistory } = loginHistorySlice.actions;
export const loginHistoryReducer = loginHistorySlice.reducer;
