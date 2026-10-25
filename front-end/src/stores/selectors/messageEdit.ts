import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectBots = (state: RootState) => state.bots;
const selectMessages = (state: RootState) => state.messages;
const selectStations = (state: RootState) => state.stations;

export const selectMessageEditLoading = createSelector(
  [selectBots, selectMessages, selectStations],
  (bots, messages, stations) =>
    bots.loading || messages.loading || stations.loading,
);
