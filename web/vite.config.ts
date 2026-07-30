import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      sitedata: path.resolve(__dirname, "..", "site", "data"),
    },
  },
  test: { globals: true, environment: "jsdom", setupFiles: "./src/setupTests.ts" },
});
