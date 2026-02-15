import { createSlice, PayloadAction } from "@reduxjs/toolkit";
import { UsersState, ServerUserItem, UserReportMode } from "../types";
import { fetchUsers, saveUsers, generateUserToken, deleteUserToken, createUser } from "../thunks";
import { ObjectId } from "../../schemas";

const initialState: UsersState = {
  users: [],
  loading: false,
  creating: false,
  error: null,
};

export type UpdateUserActionPayload = {
  id?: ObjectId;
  name?: string;
  password?: string;
  isActive?: boolean;
  isReporter?: boolean;
  reportMode?: UserReportMode;
};

export type CreateUserPayload = {
  name: string;
  isReporter: boolean;
};

export const usersSlice = createSlice({
  name: 'users',
  initialState: initialState,
  reducers: {
    updateUser(state, { payload }: PayloadAction<UpdateUserActionPayload>) {
      const user = state.users.find(u => u.id === payload.id);
      if (user) {
        user.name = payload.name ?? user.name;
        user.password = payload.password ?? user.password;
        user.isActive = payload.isActive ?? user.isActive;
        user.isReporter = payload.isReporter ?? user.isReporter;
        user.reportMode = payload.reportMode ?? user.reportMode;
        user.changed = true;
      }
    },
    userSaved(state, { payload: userId }: PayloadAction<ObjectId>) {
      const user = state.users.find(u => u.id === userId);
      if (user) {
        user.changed = false;
      }
    },
    startCreatingUser(state) {
      state.creating = true;
    },
    cancelCreatingUser(state) {
      state.creating = false;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchUsers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchUsers.fulfilled, (state, action: PayloadAction<Array<ServerUserItem>>) => {
        state.users = action.payload.map(user => ({ ...user, changed: false, password: '', apiKey: user.apiKey || null }));
        state.loading = false;
        state.creating = false;
      })
      .addCase(fetchUsers.rejected, (state, action) => {
        state.loading = false;
        state.error = typeof action.payload === 'string' ? action.payload : action.error?.message || 'Failed to fetch users';
      });
    builder
      .addCase(saveUsers.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(saveUsers.fulfilled, (state) => {
        state.loading = false;
        state.creating = false;
      })
      .addCase(saveUsers.rejected, (state, action) => {
        state.loading = false;
        state.error = typeof action.payload === 'string' ? action.payload : action.error?.message || 'Failed to save users';
      });
    builder
      .addCase(generateUserToken.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(generateUserToken.fulfilled, (state, action) => {
        state.loading = false;
        if (action.payload.success && action.payload.token) {
          const userId = action.meta.arg; 
          const user = state.users.find(u => u.id === userId);
          if (user) {
            user.apiKey = action.payload.token;
          }
        }
      })
      .addCase(generateUserToken.rejected, (state, action) => {
        state.loading = false;
        state.error = typeof action.payload === 'string' ? action.payload : action.error?.message || 'Failed to generate token';
      });
    builder
      .addCase(deleteUserToken.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteUserToken.fulfilled, (state, action) => {
        state.loading = false;
        const userId = action.meta.arg; 
        const user = state.users.find(u => u.id === userId);
        if (user) {
          user.apiKey = null;
        }
      })
      .addCase(deleteUserToken.rejected, (state, action) => {
        state.loading = false;
        state.error = typeof action.payload === 'string' ? action.payload : action.error?.message || 'Failed to delete token';
      });
    builder
      .addCase(createUser.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(createUser.fulfilled, (state) => {
        state.loading = false;
        state.creating = false;
      })
      .addCase(createUser.rejected, (state, action) => {
        state.loading = false;
        state.creating = false;
        state.error = typeof action.payload === 'string' ? action.payload : action.error?.message || 'Failed to create user';
      });
  },
});

export const { updateUser, userSaved, startCreatingUser, cancelCreatingUser } = usersSlice.actions;
export const usersReducer = usersSlice.reducer;
