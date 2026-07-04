import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { BuildingListItem, BuildingsState } from "../types";
import { startEditingBuilding, fetchBuildings, deleteBuilding, editBuildingOrder } from "../thunks";
import { BuildingEditType, ObjectId } from "../../schemas";

const initialState: BuildingsState = {
  items: [],
  edittedItems: [],
  loading: false,
  error: null,
  changed: false,
  globalId: 0,
};

export const buildingsSlice = createSlice({
  name: 'buildings',
  initialState: initialState,
  reducers: {
    startCreatingBuilding(state) {
      state.editingItem = {
        id: (state.globalId + 1).toString().padStart(24, 'f'),
        name: {},
        color: 'blue.4',
        stationId: null,
        reportUserIds: [],
        enabled: false,
        order: Math.max(state.items.length, state.edittedItems.length) + 1,
      };
    },
    finishCreatingBuilding(state, { payload }: PayloadAction<BuildingEditType>) {
      state.edittedItems.push({
        ...payload,
        isNew: true,
      });
      delete state.editingItem;
      state.changed = true;
    },
    finishEditingBuilding(state, { payload }: PayloadAction<BuildingEditType>) {
      const itemIndex = state.items.findIndex(i => i.id === payload.id);
      const edittedItemIndex = state.edittedItems.findIndex(i => i.id === payload.id);

      if (itemIndex >= 0) {
        state.items[itemIndex] = {
          ...state.items[itemIndex],
          ...payload,
          id: payload.id!,
        };
      }

      if (edittedItemIndex >= 0) {
        state.edittedItems[edittedItemIndex] = {
          ...state.edittedItems[edittedItemIndex],
          ...payload,
        };
      } else {
        state.edittedItems.push({
          ...payload,
        });
      }
      delete state.editingItem;
      state.changed = true;
    },
    cancelEditingOrCreatingBuilding(state) {
      delete state.editingItem;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchBuildings.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchBuildings.fulfilled, (state, action: PayloadAction<Array<BuildingListItem>>) => {
        state.items = action.payload;
        state.edittedItems = [];
        state.loading = false;
        state.changed = false;
        state.globalId = state.items.length + state.edittedItems.length;
      })
      .addCase(fetchBuildings.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
    builder
      .addCase(startEditingBuilding.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(startEditingBuilding.fulfilled, (state, action: PayloadAction<BuildingEditType>) => {
        state.editingItem = action.payload;
        state.loading = false;
      })
      .addCase(startEditingBuilding.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
    builder
      .addCase(deleteBuilding.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteBuilding.fulfilled, (state, { payload }: PayloadAction<ObjectId>) => {
        const edittedItemIndex = state.edittedItems.findIndex(i => i.id === payload);
        if (edittedItemIndex >= 0) {
          state.edittedItems.splice(edittedItemIndex, 1);
        }
        const itemIndex = state.items.findIndex(i => i.id === payload);
        if (itemIndex >= 0) {
          state.items.splice(itemIndex, 1);
        }
        state.loading = false;
      })
      .addCase(deleteBuilding.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      });
    builder
      .addCase(editBuildingOrder.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(editBuildingOrder.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(editBuildingOrder.fulfilled, (state, { payload }: PayloadAction<BuildingEditType[]>) => {
        payload.forEach(editedBuilding => {
          const editedIndex = state.edittedItems.findIndex(
            b => b.id === editedBuilding.id,
          );

          if (editedIndex >= 0) {
            state.edittedItems[editedIndex] = editedBuilding;
          } else {
            state.edittedItems.push(editedBuilding);
          }

          const itemIndex = state.items.findIndex(
            item => item.id === editedBuilding.id,
          );

          if (itemIndex >= 0) {
            state.items[itemIndex].order = editedBuilding.order;
          }
        });
        state.items.sort((a, b) => a.order - b.order);
        state.changed = true;
        state.loading = false;
      });
  },
});

export const {
  startCreatingBuilding,
  finishCreatingBuilding,
  finishEditingBuilding,
  cancelEditingOrCreatingBuilding,
} = buildingsSlice.actions;
export const buildingsReducer = buildingsSlice.reducer;