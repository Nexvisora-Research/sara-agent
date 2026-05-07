import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  root: path.resolve('src/renderer'),
  base: './',
  build: {
    outDir: path.resolve('dist/renderer'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
  },
  resolve: {
    alias: {
      '@': path.resolve('src/renderer'),
    },
  },
});
