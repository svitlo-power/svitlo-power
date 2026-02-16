import { createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";
import { ExtDeviceItem } from "../types";

export const fetchExtDevices = createAsyncThunk<ExtDeviceItem[]>(
    "extDevices/fetchAll",
    async (_, { rejectWithValue }) => {
        try {
            const response = await axios.get<ExtDeviceItem[]>("/api/ext-device");
            return response.data;
        } catch (error: any) {
            return rejectWithValue(error.response?.data?.detail || error.message);
        }
    }
);
