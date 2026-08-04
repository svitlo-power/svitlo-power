import { createAsyncThunk } from "@reduxjs/toolkit";
import { StationConnectionEditItem, ServerStationConnectionItem } from "../types";
import { ObjectId } from "../../schemas";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";


export const fetchStationConnections = createAsyncThunk('stationConnections/fetch', async (_, thunkAPI) => {
  try {
    const response = await apiClient.get<Array<ServerStationConnectionItem>>('/station-connections');
    return response.data;
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch connections');
  }
});

export const createStationConnection = createAsyncThunk(
  'stationConnections/create',
  async (connection: StationConnectionEditItem, thunkAPI) => {
    try {
      await apiClient.post('/station-connections', connection);
      thunkAPI.dispatch(fetchStationConnections());
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to create connection');
    }
  }
);

export type SaveStationConnectionPayload = {
  id: ObjectId;
  connection: StationConnectionEditItem;
};

export const saveStationConnection = createAsyncThunk(
  'stationConnections/save',
  async ({ id, connection }: SaveStationConnectionPayload, thunkAPI) => {
    try {
      const serverDto = {
        ...connection,
        // Empty secrets mean "keep the stored values" - never send them back
        appSecret: connection.appSecret || null,
        password: connection.password || null,
      };
      await apiClient.put(`/station-connections/${id}`, serverDto);
      thunkAPI.dispatch(fetchStationConnections());
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to save connection');
    }
  }
);

export const deleteStationConnection = createAsyncThunk(
  'stationConnections/delete',
  async (id: ObjectId, thunkAPI) => {
    try {
      await apiClient.delete(`/station-connections/${id}`);
      thunkAPI.dispatch(fetchStationConnections());
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to delete connection');
    }
  }
);
