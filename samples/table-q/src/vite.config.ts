import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      manifest: {
        name: "TableQ Store Tablet",
        short_name: "TableQ",
        theme_color: "#201e1d",
        background_color: "#f3f2f2",
        display: "standalone",
        start_url: "/",
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,woff2}"],
        navigateFallbackDenylist: [/^\/api\//],
      },
    }),
  ],
  server: {
    port: 5174,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:3100" },
  },
  build: { outDir: "dist" },
});
