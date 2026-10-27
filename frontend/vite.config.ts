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
