import { createAsyncThunk } from "@reduxjs/toolkit";
import { BaseSaveDataResponse, BaseServerStationItem, ServerStationItem } from "../types";
import { RootState } from "../store";
import { stationStateSaved } from "../slices";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";


export const fetchStations = createAsyncThunk('stations/fetchStations', async (_, thunkAPI) => {
  try {
    const response = await apiClient.post<Array<ServerStationItem>>('/stations/stations');
    return response.data;
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch stations');
  }
});

export const saveStations = createAsyncThunk('stations/saveStationData', async (_, { getState, dispatch }) => {
  try {
    const state = getState() as RootState;
    const stationsState = state.stations;
    const promises = stationsState.stations.filter(s => s.changed).map(async station => {
      const serverDto = {
        id: station.id,
        enabled: station.enabled,
        order: station.order,
        batteryCapacity: station.batteryCapacity,
        alias: station.stationAlias,
      } as BaseServerStationItem;
      const response = await apiClient.put<BaseSaveDataResponse>('/stations/save', serverDto);
      dispatch(stationStateSaved(response.data.id));
    });
    await Promise.all(promises);
    dispatch(fetchStations());
  } catch (error: unknown) {
    console.error(error);
  }
});

export const cancelStationsEditing = createAsyncThunk('stations/cancelEditing', async (_, { dispatch }) => {
  dispatch(fetchStations());
});
