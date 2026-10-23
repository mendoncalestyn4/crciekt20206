// The website is built into dist/, which the stats server (python -m server) serves. While working on it,
// `npm run dev` serves it with live reload and passes /api questions on to a server running on port 8601.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:8601" } },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    chunkSizeWarningLimit: 900,
    rollupOptions: { output: { manualChunks: { charts: ["echarts"] } } },
  },
});
