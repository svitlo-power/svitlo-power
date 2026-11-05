import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";
import "@mantine/core/styles.css";
import "@mantine/dates/styles.css";
import "@mantine/charts/styles.css";
import "./icons.ts";
import "./i18n";
import { store } from "./stores/store";
import { appStarted } from "./stores/slices";
import { fetchAppVersion } from "./stores/thunks";

store.dispatch(appStarted());
store.dispatch(fetchAppVersion());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
