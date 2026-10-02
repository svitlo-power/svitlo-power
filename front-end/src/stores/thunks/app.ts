import { createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";
import { setVersion } from "../slices/app";

// Create a separate axios instance for version endpoint (served at root, not /api)
export const versionClient = axios.create({
  baseURL: "/",
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
  }
);