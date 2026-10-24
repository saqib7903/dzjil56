import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the API runs separately on :8000; proxy /api so the app can
// use same-origin URLs everywhere (dev, Docker and Vercel).
export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: { charts: ['recharts'] },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': process.env.VITE_DEV_API_TARGET || 'http://localhost:8000',
    },
  },
});
