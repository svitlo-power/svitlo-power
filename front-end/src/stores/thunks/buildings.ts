import { createAsyncThunk } from "@reduxjs/toolkit";
import apiClient from "../../utils/apiClient";
import { getErrorMessage } from "../../utils";
import { BuildingListItem, BuildingsState } from "../types";
import { BuildingEditType, ObjectId } from "../../schemas";
import { RootState } from "../store";

export type ChangeBuildingOrderPayload = {
  currentOrder: number;
  delta: number;
};

export const fetchBuildings = createAsyncThunk('buildings/fetchBuildings', async (_, thunkAPI) => {
  try {
    const response = await apiClient.get<Array<BuildingListItem>>('/dashboard/buildings');
    return response.data;
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch buildings');
  }
});

const getBuildingEditData = async (state: BuildingsState, buildingId: ObjectId): Promise<BuildingEditType> => {
  const building = state.edittedItems.find(b => b.id === buildingId);
  if (building) {
    return building;
  }
  const response = await apiClient.get<BuildingEditType>(`/dashboard/buildings/${buildingId}`);
  return response.data;
};

const findBuildingIdByOrder = (state: BuildingsState, order: number): string | undefined => {
  const building = state.edittedItems.find(b => b.order === order);
  if (building) {
    return building.id!;
  }
  return state.items.find(b => b.order === order)?.id;
};

export const editBuildingOrder = createAsyncThunk(
  'buildings/editBuildingOrder',
  async (payload: ChangeBuildingOrderPayload, thunkAPI) => {
    try {
      const state = (thunkAPI.getState() as RootState).buildings;
      const { currentOrder, delta } = payload;
      const newOrder = currentOrder + delta;
      const maxOrder = Math.max(state.items.length, state.edittedItems.length);
      if (newOrder < 1 || newOrder > maxOrder) {
        return [];
      }

      const buildingAId = findBuildingIdByOrder(state, currentOrder);
      const buildingBId = findBuildingIdByOrder(state, newOrder);

      const buildingPromises = [
        getBuildingEditData(state, buildingAId!),
        getBuildingEditData(state, buildingBId!),
      ];

      const fetchedBuildings = await Promise.all(buildingPromises);

      const editedBuildings = [
        {
          ...fetchedBuildings.find(b => b.id === buildingAId)!,
          order: newOrder,
        } as BuildingEditType,
        {
          ...fetchedBuildings.find(b => b.id === buildingBId)!,
          order: currentOrder,
        } as BuildingEditType,
      ];

      return thunkAPI.fulfillWithValue(editedBuildings);
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to edit building order');
    }
  },
);

export const startEditingBuilding = createAsyncThunk('buildings/startEditingBuilding', async (buildingId: ObjectId, thunkAPI) => {
  try {
    const state = (thunkAPI.getState() as RootState).buildings;
    return await getBuildingEditData(state, buildingId);
  } catch (error: unknown) {
    return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch building edit data');
  }
});

export const saveBuildings = createAsyncThunk('buildings/saveBuildings', async (_, { getState, dispatch }) => {
  try {
    const state = getState() as RootState;
    const buildingsState = state.buildings;
    const promises = buildingsState.edittedItems.map(async building => {
      const serverDto = {
        name: building.name,
        color: building.color,
        stationId: building.stationId,
        reportUserIds: building.reportUserIds,
        enabled: building.enabled,
        order: building.order,
      } as BuildingEditType;
      if (building.isNew) {
        await apiClient.post('/dashboard/buildings', serverDto);
      } else {
        await apiClient.put(`/dashboard/buildings/${building.id}`, serverDto);
      }
    });
    await Promise.all(promises);
    dispatch(fetchBuildings());
  } catch (error: unknown) {
    console.error(error);
  }  
});

export const deleteBuilding = createAsyncThunk('buildings/deleteBuilding', async (buildingId: ObjectId, { getState }) => {
  try {
    const state = getState() as RootState;
    const building = state.buildings.edittedItems.find(f => f.id === buildingId);
    if (building?.isNew) {
      return buildingId;
    }
    await apiClient.delete(`/dashboard/buildings/${buildingId}`);
    return buildingId;
  } catch (error: unknown) {
    console.error(error);
    throw error;
  }
});
