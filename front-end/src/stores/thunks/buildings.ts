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

type BuildingOrderUpdatePayload = {
  building: BuildingEditType;
  previousOrder: number;
  updatedOrder: number;
};

export const fetchBuildings = createAsyncThunk(
  'buildings/fetchBuildings',
  async (_, thunkAPI) => {
    try {
      const response = await apiClient.get<Array<BuildingListItem>>('/dashboard/buildings');
      return response.data;
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch buildings');
    }
  },
);

const getBuildingEditData = async (
  state: BuildingsState,
  buildingId: ObjectId,
): Promise<BuildingEditType> => {
  const building = state.edittedItems.find(b => b.id === buildingId);
  if (building) {
    return building;
  }
  const response = await apiClient.get<BuildingEditType>(`/dashboard/buildings/${buildingId}`);
  return response.data;
};

const getVisibleBuildings = (state: BuildingsState) => {
  const mergedBuildings = state.items
    .filter(item => item.id && !state.deletedItems.includes(item.id))
    .map(item => {
      const editedBuilding = state.edittedItems.find(eb => eb.id === item.id);
      return editedBuilding ? { ...item, ...editedBuilding } : item;
    });

  const newBuildings = state.edittedItems.filter(item =>
    item.id && !state.items.some(existing => existing.id === item.id) && !state.deletedItems.includes(item.id),
  );

  return [...mergedBuildings, ...newBuildings].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
};

const findBuildingIdByOrder = (state: BuildingsState, order: number): ObjectId | undefined => {
  const buildingId = getVisibleBuildings(state).find(building => building.order === order)?.id;
  return buildingId ?? undefined;
};

export const editBuildingOrder = createAsyncThunk(
  'buildings/editBuildingOrder',
  async (payload: ChangeBuildingOrderPayload, thunkAPI) => {
    try {
      const state = (thunkAPI.getState() as RootState).buildings;
      const { currentOrder, delta } = payload;
      const newOrder = currentOrder + delta;
      const visibleBuildings = getVisibleBuildings(state);
      const maxOrder = visibleBuildings.length;
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

      const editedBuildings: BuildingOrderUpdatePayload[] = [
        {
          building: {
            ...fetchedBuildings.find(b => b.id === buildingAId)!,
            order: newOrder,
          } as BuildingEditType,
          previousOrder: currentOrder,
          updatedOrder: newOrder,
        },
        {
          building: {
            ...fetchedBuildings.find(b => b.id === buildingBId)!,
            order: currentOrder,
          } as BuildingEditType,
          previousOrder: newOrder,
          updatedOrder: currentOrder,
        },
      ];

      return thunkAPI.fulfillWithValue(editedBuildings);
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to edit building order');
    }
  },
);

export const startEditingBuilding = createAsyncThunk(
  'buildings/startEditingBuilding',
  async (buildingId: ObjectId, thunkAPI) => {
    try {
      const state = (thunkAPI.getState() as RootState).buildings;
      return await getBuildingEditData(state, buildingId);
    } catch (error: unknown) {
      return thunkAPI.rejectWithValue(getErrorMessage(error) || 'Failed to fetch building edit data');
    }
  },
);

export const saveBuildings = createAsyncThunk(
  'buildings/saveBuildings',
  async (_, { getState, dispatch }) => {
    try {
      const state = getState() as RootState;
      const buildingsState = state.buildings;
      const deletedBuildingIds = new Set(buildingsState.deletedItems.map(id => String(id)));

      const deletePromises = buildingsState.deletedItems
        .filter(buildingId => {
          const relatedBuilding = buildingsState.edittedItems.find(item => String(item.id) === String(buildingId));
          return !relatedBuilding?.isNew;
        })
        .map(async buildingId => {
          if (!buildingId) {
            return;
          }
          await apiClient.delete(`/dashboard/buildings/${buildingId}`);
        });

      const savePromises = buildingsState.edittedItems
        .filter((building: BuildingEditType & { isNew?: boolean }) => !deletedBuildingIds.has(String(building.id)))
        .map(async (building: BuildingEditType & { isNew?: boolean }) => {
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

      await Promise.all([...deletePromises, ...savePromises]);
      dispatch(fetchBuildings());
    } catch (error: unknown) {
      console.error(error);
    }
  },
);
