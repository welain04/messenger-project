import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";

// Basic Vite config for React + TS + Tailwind
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173
  }
});

