import { createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";
import {
  setFeatures,
  setFeaturesLoaded,
  setBackendVersion,
  setVersion,
} from "../slices/app";

// Create a separate axios instance for version endpoint (served at root, not /api)
export const versionClient = axios.create({
  baseURL: "/",
});

const backendAppClient = axios.create({
  baseURL: "/api",
});

export const fetchAppVersion = createAsyncThunk(
  "app/fetchAppVersion",
  async (_, { dispatch }) => {
    try {
      const response = await versionClient.get<string>("/version");
      if (response.status === 200) {
        dispatch(setVersion(response.data.trim()));
      }
    } catch (error) {
      console.warn("Failed to fetch app version:", error);
    }

    try {
      const response = await backendAppClient.get<{
        dashboardUpdatedEventEnabled: boolean;
      }>("/app/features");
      if (response.status === 200) {
        dispatch(setFeatures(response.data));
      }
    } catch (error) {
      console.warn("Failed to fetch backend features:", error);
    } finally {
      dispatch(setFeaturesLoaded());
    }

    try {
      const response = await backendAppClient.get<string>("/app/version");
      if (response.status === 200) {
        dispatch(setBackendVersion(response.data.trim()));
      }
    } catch (error) {
      console.warn("Failed to fetch backend version:", error);
    }
  },
);
