import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The frontend talks to the FastAPI backend via the `/api` prefix, which Vite
// proxies to the backend in development so there are no CORS surprises.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
