import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectUsers = (state: RootState) => state.users.users;

export const selectUsersChanged = createSelector([selectUsers], (users) =>
  users.some((user) => user.changed),
);
