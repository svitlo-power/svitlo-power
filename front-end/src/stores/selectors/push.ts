import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectPushDevices = (state: RootState) => state.pushDevices;
const selectPushTopics = (state: RootState) => state.pushTopics;

export const selectPushLoading = createSelector(
  [selectPushDevices, selectPushTopics],
  (devices, topics) => devices.loading || topics.loading,
);

export const selectPushError = createSelector(
  [selectPushDevices, selectPushTopics],
  (devices, topics) => devices.error ?? topics.error,
);
