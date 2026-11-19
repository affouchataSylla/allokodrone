import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: process.env.VITE_BASE || "/",
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8080",
      "/admin": "http://127.0.0.1:8080",
      "/assets": "http://127.0.0.1:8080",
      "/css": "http://127.0.0.1:8080",
      "/fonts": "http://127.0.0.1:8080",
      "/images": "http://127.0.0.1:8080",
      "/js": "http://127.0.0.1:8080",
      "/videos": "http://127.0.0.1:8080",
      "/menu.pdf": "http://127.0.0.1:8080",
    },
  },
});
