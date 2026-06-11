import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// Basic Vite config for React + TS + Tailwind
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true
  }
});

