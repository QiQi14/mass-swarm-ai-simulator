import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  server: {
    port: 5173,
    open: '/',
    // Note: /logs is served from public/logs symlink → ../../macro-brain/runs
    // Do NOT proxy /logs to the Rust WS server — it has no HTTP endpoint.
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        playground: resolve(__dirname, 'index.html'),
        training: resolve(__dirname, 'training.html'),
      },
    },
  },
});
