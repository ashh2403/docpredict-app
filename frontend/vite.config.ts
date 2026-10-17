import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The browser always calls same-origin "/api"; Vite forwards it to the FastAPI backend.
const backend = process.env.DOCPREDICT_API_URL ?? "http://127.0.0.1:8000";
const proxy = { "/api": { target: backend, changeOrigin: true } };

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true, proxy },
  preview: { port: 4173, strictPort: true, proxy },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    testTimeout: 20000,
  },
});
