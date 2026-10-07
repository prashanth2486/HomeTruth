import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/localities": "http://127.0.0.1:8000",
      "/listings": "http://127.0.0.1:8000",
      "/map": "http://127.0.0.1:8000",
      "/analyze": "http://127.0.0.1:8000",
      "/compare": "http://127.0.0.1:8000",
      "/report": "http://127.0.0.1:8000",
      "/chat": "http://127.0.0.1:8000",
      "/auth": "http://127.0.0.1:8000",
    },
  },
});
