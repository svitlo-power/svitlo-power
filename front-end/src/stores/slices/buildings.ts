import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { BuildingListItem, BuildingsState } from "../types";
import { startEditingBuilding, fetchBuildings, editBuildingOrder } from "../thunks";
import { BuildingEditType, ObjectId } from "../../schemas";

const getVisibleBuildings = <T extends { id?: ObjectId | null; order: number }>(
  items: Array<T>,
  deletedItems: ObjectId[],
): Array<T> => items.filter(item => item.id && !deletedItems.includes(item.id));

const reSequenceBuildings = <T extends { id?: ObjectId | null; order: number }>(
  items: Array<T>,
  deletedItems: ObjectId[],
) => {
  const visibleItems = getVisibleBuildings(items, deletedItems).sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
  visibleItems.forEach((item, index) => {
    item.order = index + 1;
  });
};

const initialState: BuildingsState = {
  items: [],
  edittedItems: [],
  loading: false,
  error: null,
  deletedItems: [],
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
        order: getVisibleBuildings(state.items, state.deletedItems).length + 1,
      };
    },
    finishCreatingBuilding(state, { payload }: PayloadAction<BuildingEditType>) {
      const creatingBuilding = state.editingItem;
      const newBuilding = {
        ...creatingBuilding,
        ...payload,
        id: creatingBuilding?.id ?? payload.id,
        order: creatingBuilding?.order ?? payload.order ?? 1,
        isNew: true,
      } as BuildingEditType & { isNew?: boolean };
      state.edittedItems.push(newBuilding as BuildingEditType);
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
    markBuildingForDeletion(state, { payload }: PayloadAction<ObjectId>) {
      const newBuilding = state.edittedItems.some((item: BuildingEditType & { isNew?: boolean }) => item.id === payload && item.isNew);

      if (newBuilding) {
        state.edittedItems = state.edittedItems.filter((item: BuildingEditType & { isNew?: boolean }) => item.id !== payload);
        state.items = state.items.filter((item: BuildingListItem) => item.id !== payload);
        state.deletedItems = state.deletedItems.filter((item: ObjectId) => item !== payload);
        state.changed = true;
        return;
      }

      if (!state.deletedItems.includes(payload)) {
        state.deletedItems.push(payload);
      }

      reSequenceBuildings(state.items, state.deletedItems);
      reSequenceBuildings(state.edittedItems, state.deletedItems);
      state.changed = true;
    },
    undoBuildingDeletion(state, { payload }: PayloadAction<ObjectId>) {
      state.deletedItems = state.deletedItems.filter((item: ObjectId) => item !== payload);
      reSequenceBuildings(state.items, state.deletedItems);
      reSequenceBuildings(state.edittedItems, state.deletedItems);
      state.changed = true;
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
        state.deletedItems = [];
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
      .addCase(editBuildingOrder.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(editBuildingOrder.rejected, (state, action: PayloadAction<unknown>) => {
        state.loading = false;
        state.error = action.payload as string;
      })
      .addCase(editBuildingOrder.fulfilled, (state, { payload }: PayloadAction<Array<{ building: BuildingEditType; previousOrder: number; updatedOrder: number }>>) => {
        payload.forEach(({ building, updatedOrder }) => {
          const editedIndex = state.edittedItems.findIndex((item: BuildingEditType & { isNew?: boolean }) => item.id === building.id);

          if (editedIndex >= 0) {
            state.edittedItems[editedIndex] = {
              ...state.edittedItems[editedIndex],
              ...building,
              order: updatedOrder,
            };
          } else if (building.id) {
            state.edittedItems.push({
              ...building,
              order: updatedOrder,
            });
          }

          const itemIndex = state.items.findIndex(item => item.id === building.id);

          if (itemIndex >= 0) {
            const currentItem = state.items[itemIndex];
            state.items[itemIndex] = {
              ...currentItem,
              ...building,
              id: building.id ?? currentItem.id,
              order: updatedOrder,
            } as BuildingListItem;
          }
        });
        state.items.sort((a, b) => a.order - b.order);
        state.edittedItems.sort((a, b) => a.order - b.order);
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
  markBuildingForDeletion,
  undoBuildingDeletion,
} = buildingsSlice.actions;
export const buildingsReducer = buildingsSlice.reducer;