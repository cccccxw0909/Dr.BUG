import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

/** Align with backend.config.STATIC_PORT (default 8001) for the dev proxy */
const API_TARGET = process.env.VITE_PROXY_TARGET || "http://127.0.0.1:8001";

const apiProxy = { target: API_TARGET, changeOrigin: true };

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // Each pattern ends with (/|$) so /prediction does not prefix-match /predictionals, etc.
      "^/prediction(/|$)": apiProxy,
      "^/pending-actions(/|$)": apiProxy,
      "^/datasets(/|$)": apiProxy,
      "^/models(/|$)": apiProxy,
      "^/tasks(/|$)": apiProxy,
      "^/chat(/|$)": apiProxy,
      "^/actions(/|$)": apiProxy,
      "^/static(/|$)": apiProxy,
      "^/health(/|$)": apiProxy,
      "^/recommendation(/|$)": apiProxy,
    },
  },
});

