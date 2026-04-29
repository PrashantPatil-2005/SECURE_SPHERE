import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        configure: (proxy) => {
          proxy.on('error', () => {
            // Backend offline — frontend already handles via mock-data
            // fallback. Swallow ECONNREFUSED so the dev console isn't
            // drowned in proxy stack traces.
          });
        },
      },
      '/socket.io': {
        target: 'http://localhost:8000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', () => {});
        },
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
