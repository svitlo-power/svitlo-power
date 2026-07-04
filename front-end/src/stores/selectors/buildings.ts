import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectEdittedBuildings = (state: RootState) => state.buildings.edittedItems;
const selectExistingBuildings = (state: RootState) => state.buildings.items;
const selectDeletedBuildingIds = (state: RootState) => state.buildings.deletedItems;

export const createSelectEdittedBuildings = createSelector(
  [selectExistingBuildings, selectEdittedBuildings, selectDeletedBuildingIds],
  (existingBuildings, edittedBuildings, deletedBuildingIds) => {
    const visibleBuildings = [
      ...existingBuildings.filter(building => !deletedBuildingIds.includes(building.id!)),
      ...edittedBuildings.filter(eb =>
        !existingBuildings.some(edb => edb.id === eb.id)
        && !deletedBuildingIds.includes(eb.id!),
      ),
    ].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));

    return visibleBuildings;
  },
);