import { createSlice } from "@reduxjs/toolkit";
import { ExtDevicesState } from "../types";
import { fetchExtDevices } from "../thunks";

const initialState: ExtDevicesState = {
    items: [],
    loading: false,
    error: null,
};

const extDevicesSlice = createSlice({
    name: "extDevices",
    initialState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchExtDevices.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchExtDevices.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchExtDevices.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            });
    },
});

export const extDevicesReducer = extDevicesSlice.reducer;
