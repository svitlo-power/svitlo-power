import { createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../../utils/apiClient";
import { LoginHistoryItem } from "../types";
import { getErrorMessage } from "../../utils";
import { ObjectId } from "../../schemas";

type LoginHistoryResponse = LoginHistoryItem[];

export const fetchLoginHistory = createAsyncThunk(
  'loginHistory/fetchLoginHistory',
  async ({ userId }: { userId: ObjectId; }, thunkAPI) => {
    try {
      const response = await apiClient.get<LoginHistoryResponse>(`/users/login-history/${userId}`);
      return response.data;
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch login history');
    }
  }
);
