import { createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";
import { ObjectId } from "../../schemas";
import { PushDeviceItem, PushSendResult, PushTestRequest, PushTopicItem } from "../types";

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

export const sendTestPush =createAsyncThunk<PushSendResult, PushTestRequest>(
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
