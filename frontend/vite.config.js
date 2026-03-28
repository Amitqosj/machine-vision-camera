import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: {
      "/api": {
        target: "https://machine-vision-camera-backend.onrender.com",
        changeOrigin: true,
      },
      "/health": {
        target: "https://machine-vision-camera-backend.onrender.com",
        changeOrigin: true,
      },
    },
  },
});

