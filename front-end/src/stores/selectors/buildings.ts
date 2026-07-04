import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectEdittedBuildings = (state: RootState) => state.buildings.edittedItems;
const selectExistingBuildings = (state: RootState) => state.buildings.items;

export const createSelectEdittedBuildings = createSelector(
  [selectExistingBuildings, selectEdittedBuildings],
  (existingBuildings, edittedBuildings) => [
    ...existingBuildings,
    ...edittedBuildings.filter(eb => !existingBuildings.some(edb => edb.id === eb.id)),
  ].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
);