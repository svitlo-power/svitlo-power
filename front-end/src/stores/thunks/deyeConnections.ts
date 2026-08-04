import { createAsyncThunk } from "@reduxjs/toolkit";
import { DeyeConnectionEditItem, ServerDeyeConnectionItem } from "../types";
import { ObjectId } from "../../schemas";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";


export const fetchDeyeConnections = createAsyncThunk('deyeConnections/fetch', async (_, thunkAPI) => {
  try {
    const response = await apiClient.get<Array<ServerDeyeConnectionItem>>('/deye-connections');
    return response.data;
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch connections');
  }
});

export const createDeyeConnection = createAsyncThunk(
  'deyeConnections/create',
  async (connection: DeyeConnectionEditItem, thunkAPI) => {
    try {
      await apiClient.post('/deye-connections', connection);
      thunkAPI.dispatch(fetchDeyeConnections());
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to create connection');
    }
  }
);

export type SaveDeyeConnectionPayload = {
  id: ObjectId;
  connection: DeyeConnectionEditItem;
};

export const saveDeyeConnection = createAsyncThunk(
  'deyeConnections/save',
  async ({ id, connection }: SaveDeyeConnectionPayload, thunkAPI) => {
    try {
      const serverDto = {
        ...connection,
        // Empty secrets mean "keep the stored values" - never send them back
        appSecret: connection.appSecret || null,
        password: connection.password || null,
      };
      await apiClient.put(`/deye-connections/${id}`, serverDto);
      thunkAPI.dispatch(fetchDeyeConnections());
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to save connection');
    }
  }
);

export const deleteDeyeConnection = createAsyncThunk(
  'deyeConnections/delete',
  async (id: ObjectId, thunkAPI) => {
    try {
      await apiClient.delete(`/deye-connections/${id}`);
      thunkAPI.dispatch(fetchDeyeConnections());
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to delete connection');
    }
  }
);
