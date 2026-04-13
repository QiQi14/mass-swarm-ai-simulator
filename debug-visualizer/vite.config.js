import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  server: {
    port: 5173,
    open: true,
    // Note: /logs is served from public/logs symlink → ../../macro-brain/runs
    // Do NOT proxy /logs to the Rust WS server — it has no HTTP endpoint.
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
});
