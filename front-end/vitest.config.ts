import { defineConfig, mergeConfig } from "vitest/config";
import viteConfig from "./vite.config";
import react from "@vitejs/plugin-react";

export default mergeConfig(
  viteConfig,
  defineConfig({
    plugins: [react({ jsxRuntime: "classic" })],
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["src/test/setup.ts"],
      testTimeout: 30000,
      server: {
        deps: {
          inline: ["@mantine/core", "@mantine/hooks", "@reduxjs/toolkit", "react-redux"],
        },
      },
    },
  }),
);