import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://api:8000",
        changeOrigin: true,
      },
      "/demo/orders": { target: "http://orders-api:8080", changeOrigin: true, rewrite: (path) => path.replace(/^\/demo\/orders/, "") },
      "/demo/inventory": { target: "http://inventory-api:8080", changeOrigin: true, rewrite: (path) => path.replace(/^\/demo\/inventory/, "") },
      "/demo/payments": { target: "http://payments-api:8080", changeOrigin: true, rewrite: (path) => path.replace(/^\/demo\/payments/, "") },
      "/demo/reporting": { target: "http://reporting-worker:8080", changeOrigin: true, rewrite: (path) => path.replace(/^\/demo\/reporting/, "") },
      "/demo/notifications": { target: "http://notifications-api:8080", changeOrigin: true, rewrite: (path) => path.replace(/^\/demo\/notifications/, "") },
    },
    headers: {
      // Vite injects component CSS as <style> nodes in development. Production should serve a
      // stricter policy from its HTTPS reverse proxy; this keeps the local dev server usable.
      "Content-Security-Policy": "default-src 'self'; base-uri 'self'; object-src 'none'; frame-ancestors 'none'; form-action 'self'; connect-src 'self' ws://localhost:5174; style-src 'self' 'unsafe-inline'",
      "Permissions-Policy": "camera=(), geolocation=(), microphone=()",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "same-origin",
    },
  },
});
