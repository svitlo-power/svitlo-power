import { createSelector } from "@reduxjs/toolkit";
import { RootState } from "../store";

const selectAuth = (state: RootState) => state.auth;
const selectUsers = (state: RootState) => state.users;

export const selectProfileEditLoading = createSelector(
  [selectAuth, selectUsers],
  (auth, users) => auth.loading || users.loading,
);

export const selectProfileEditUserNames = createSelector(
  [selectUsers],
  (users) => users.users.map((user) => user.name),
);
