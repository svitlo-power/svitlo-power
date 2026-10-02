import { rootReducer } from "./rootReducer";
import { configureStore } from "@reduxjs/toolkit";
import { TypedUseSelectorHook, useDispatch, useSelector } from "react-redux";
import appMiddleware from "./middleware/app";
import authMiddleware from "./middleware/auth";
import { appStarted } from "./slices";
import { fetchAppVersion } from "./thunks";

export const store = configureStore({
  reducer: rootReducer,
  devTools: true,
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(appMiddleware.middleware, authMiddleware.middleware),
});

store.dispatch(appStarted());
store.dispatch(fetchAppVersion());

export type StoreType = typeof store;
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;

export const useAppDispatch = () => useDispatch<AppDispatch>();
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;