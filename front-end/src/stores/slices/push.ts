import { createSlice } from "@reduxjs/toolkit";
import {
    AnnouncementsState, PushDeliveriesState, PushDevicesState, PushTemplateItem, PushTemplatesState, PushTopicsState,
} from "../types";
import {
    deletePushDevice, fetchAnnouncements, fetchPushDeliveries, fetchPushDevices, fetchPushTemplates, fetchPushTopics,
    resetPushTemplate, savePushTemplate, setPushTopicState,
} from "../thunks";

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

const replaceTemplate = (state: PushTemplatesState, template: PushTemplateItem) => {
    const index = state.items.findIndex((t) => t.topic === template.topic);
    if (index >= 0) {
        state.items[index] = template;
    }
};

const initialPushTemplatesState: PushTemplatesState = {
    items: [],
    loading: false,
    error: null,
};

const pushTemplatesSlice = createSlice({
    name: "pushTemplates",
    initialState: initialPushTemplatesState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchPushTemplates.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchPushTemplates.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchPushTemplates.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            })
            .addCase(savePushTemplate.fulfilled, (state, action) => {
                replaceTemplate(state, action.payload);
            })
            .addCase(resetPushTemplate.fulfilled, (state, action) => {
                replaceTemplate(state, action.payload);
            });
    },
});

const initialPushDeliveriesState: PushDeliveriesState = {
    items: [],
    loading: false,
    error: null,
};

const pushDeliveriesSlice = createSlice({
    name: "pushDeliveries",
    initialState: initialPushDeliveriesState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchPushDeliveries.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchPushDeliveries.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchPushDeliveries.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            });
    },
});

const initialAnnouncementsState: AnnouncementsState = {
    items: [],
    loading: false,
    error: null,
};

const announcementsSlice = createSlice({
    name: "announcements",
    initialState: initialAnnouncementsState,
    reducers: {},
    extraReducers: (builder) => {
        builder
            .addCase(fetchAnnouncements.pending, (state) => {
                state.loading = true;
                state.error = null;
            })
            .addCase(fetchAnnouncements.fulfilled, (state, action) => {
                state.loading = false;
                state.items = action.payload;
            })
            .addCase(fetchAnnouncements.rejected, (state, action) => {
                state.loading = false;
                state.error = action.payload as string;
            });
    },
});

export const pushDevicesReducer = pushDevicesSlice.reducer;
export const pushTopicsReducer = pushTopicsSlice.reducer;
export const pushTemplatesReducer = pushTemplatesSlice.reducer;
export const pushDeliveriesReducer = pushDeliveriesSlice.reducer;
export const announcementsReducer = announcementsSlice.reducer;
