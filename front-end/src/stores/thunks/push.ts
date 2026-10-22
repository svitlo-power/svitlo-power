import { createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";
import { ObjectId } from "../../schemas";
import {
    AnnouncementItem, AnnouncementRequest, PushDeliveryItem, PushDeviceItem, PushSendResult, PushTemplateItem,
    PushTemplatePreview, PushTemplateRequest, PushTestRequest, PushTopicItem,
} from "../types";

export const fetchPushDevices = createAsyncThunk<PushDeviceItem[]>(
    "push/fetchDevices",
    async (_, { rejectWithValue }) => {
        try {
            const response = await apiClient.get<PushDeviceItem[]>("/push/devices");
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const deletePushDevice = createAsyncThunk<void, ObjectId>(
    "push/deleteDevice",
    async (deviceId, { dispatch, rejectWithValue }) => {
        try {
            await apiClient.delete(`/push/devices/${deviceId}`);
            dispatch(fetchPushDevices());
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const fetchPushTopics = createAsyncThunk<PushTopicItem[]>(
    "push/fetchTopics",
    async (_, { rejectWithValue }) => {
        try {
            const response = await apiClient.get<PushTopicItem[]>("/push/topics/all");
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const setPushTopicState = createAsyncThunk<void, { key: string; enabled: boolean }>(
    "push/setTopicState",
    async ({ key, enabled }, { dispatch, rejectWithValue }) => {
        try {
            await apiClient.patch(`/push/topics/${encodeURIComponent(key)}/state`, { enabled });
        } catch (error: unknown) {
            dispatch(fetchPushTopics());
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const sendTestPush = createAsyncThunk<PushSendResult, PushTestRequest>(
    "push/sendTest",
    async (request, { dispatch, rejectWithValue }) => {
        try {
            const response = await apiClient.post<PushSendResult>("/push/test", request);
            // Unregistered tokens are removed on the server while sending.
            if (response.data.removedCount > 0) {
                dispatch(fetchPushDevices());
            }
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const fetchPushTemplates = createAsyncThunk<PushTemplateItem[]>(
    "push/fetchTemplates",
    async (_, { rejectWithValue }) => {
        try {
            const response = await apiClient.get<PushTemplateItem[]>("/push/templates");
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const savePushTemplate = createAsyncThunk<PushTemplateItem, { topic: string; request: PushTemplateRequest }>(
    "push/saveTemplate",
    async ({ topic, request }, { rejectWithValue }) => {
        try {
            const response = await apiClient.put<PushTemplateItem>(`/push/templates/${encodeURIComponent(topic)}`, request);
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const resetPushTemplate = createAsyncThunk<PushTemplateItem, string>(
    "push/resetTemplate",
    async (topic, { rejectWithValue }) => {
        try {
            const response = await apiClient.post<PushTemplateItem>(`/push/templates/${encodeURIComponent(topic)}/reset`);
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const previewPushTemplate = createAsyncThunk<PushTemplatePreview, { topic: string; request: PushTemplateRequest }>(
    "push/previewTemplate",
    async ({ topic, request }, { rejectWithValue }) => {
        try {
            const response = await apiClient.post<PushTemplatePreview>(
                `/push/templates/${encodeURIComponent(topic)}/preview`, request);
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const testPushTemplate = createAsyncThunk<
    PushSendResult,
    { topic: string; deviceId: ObjectId; request: PushTemplateRequest }
>(
    "push/testTemplate",
    async ({ topic, deviceId, request }, { dispatch, rejectWithValue }) => {
        try {
            const response = await apiClient.post<PushSendResult>(
                `/push/templates/${encodeURIComponent(topic)}/test`, { ...request, deviceId });
            if (response.data.removedCount > 0) {
                dispatch(fetchPushDevices());
            }
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const fetchPushDeliveries = createAsyncThunk<PushDeliveryItem[]>(
    "push/fetchDeliveries",
    async (_, { rejectWithValue }) => {
        try {
            const response = await apiClient.get<PushDeliveryItem[]>("/push/deliveries");
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const fetchAnnouncements = createAsyncThunk<AnnouncementItem[]>(
    "announcements/fetch",
    async (_, { rejectWithValue }) => {
        try {
            const response = await apiClient.get<AnnouncementItem[]>("/announcements");
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const publishAnnouncement = createAsyncThunk<AnnouncementItem, AnnouncementRequest>(
    "announcements/publish",
    async (request, { dispatch, rejectWithValue }) => {
        try {
            const response = await apiClient.post<AnnouncementItem>("/announcements", request);
            dispatch(fetchAnnouncements());
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);

export const deleteAnnouncement = createAsyncThunk<void, ObjectId>(
    "announcements/delete",
    async (announcementId, { dispatch, rejectWithValue }) => {
        try {
            await apiClient.delete(`/announcements/${announcementId}`);
            dispatch(fetchAnnouncements());
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error));
        }
    }
);
