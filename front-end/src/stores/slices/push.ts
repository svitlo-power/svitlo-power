import { createSlice } from "@reduxjs/toolkit";
import { PushDevicesState, PushTopicsState } from "../types";
import { deletePushDevice, fetchPushDevices, fetchPushTopics, setPushTopicState } from "../thunks";

const initialDevicesState: PushDevicesState = {
    items: [],
    loading: false,
    error: null,
};

const pushDevicesSlice = createSlice({
    name: "pushDevices",
    initialState: initialDevicesState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchPushDevices.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchPushDevices.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchPushDevices.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            })
            .addCase(deletePushDevice.pending, (state) => {
                state.loading = true;
            })
            .addCase(deletePushDevice.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            });
    },
});

const initialTopicsState: PushTopicsState = {
    items: [],
    loading: false,
    error: null,
};

const pushTopicsSlice = createSlice({
    name: "pushTopics",
    initialState: initialTopicsState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchPushTopics.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchPushTopics.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchPushTopics.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            })
            // Switched optimistically; a failed request reloads the list.
            .addCase(setPushTopicState.pending, (state, action) => {
                const topic = state.items.find((t) => t.key === action.meta.arg.key);
                if (topic) {
                    topic.enabled = action.meta.arg.enabled;
                }
            });
    },
});

export const pushDevicesReducer = pushDevicesSlice.reducer;
export const pushTopicsReducer = pushTopicsSlice.reducer;
