import { createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";
import { ExtDeviceItem } from "../types";
import { getErrorMessage } from "../../utils";

export const fetchExtDevices = createAsyncThunk<ExtDeviceItem[]>(
    "extDevices/fetchAll",
    async (_, { rejectWithValue }) => {
        try {
            const response = await axios.get<ExtDeviceItem[]>("/api/ext-device");
            return response.data;
        } catch (error: unknown) {
            return rejectWithValue(getErrorMessage(error, 'Cannot fetch external devices'));
        }
    }
);
