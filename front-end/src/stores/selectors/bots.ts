import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectBots = (state: RootState) => state.bots.bots;

export const selectBotsChanged = createSelector([selectBots], (bots) =>
  bots.some((bot) => bot.changed),
);
