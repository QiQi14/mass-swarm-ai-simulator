# Task 04: Vite Config + Integration Polish

## Metadata

```yaml
Task_ID: task_04_vite_integration
Execution_Phase: 3
Model_Tier: advanced
Live_System_Impact: safe
Feature: "Training Page — Fullscreen Map + Overlay Dashboard Redesign"
```

## Target_Files

- `debug-visualizer/vite.config.js` [MODIFY]

## Dependencies

- Task 03 (`training.html` must exist at `debug-visualizer/training.html`)

## Context_Bindings

- `context/project`

## Strict_Instructions

Update the Vite configuration to support multi-page builds with both `index.html` (playground) and `training.html` (training) entry points.

### Current File Content (for reference)

```js
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
```

### Required Changes

Replace the entire content with:

```js
import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  server: {
    port: 5173,
    open: '/training.html',
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
```

### Key Changes Explained

1. **`import { resolve } from 'path'`** — Node.js built-in, needed for `rollupOptions.input` absolute paths
2. **`server.open: '/training.html'`** — Default to training page during dev (changed from `true` which opens `/`)
3. **`build.rollupOptions.input`** — Multi-page build: Rollup bundles both `index.html` and `training.html` as separate entry points with their own JS/CSS chunks

### Anti-Hallucination Notes

- `resolve` is from Node.js `'path'` module — NOT from `'url'` or Vite
- `__dirname` is available in Vite config files — Vite handles ESM→CJS bridging for config files
- Keep `publicDir: 'public'` — the `/logs` symlink lives there and must be served for training status polling
- Keep the existing comment about `/logs` proxy

### What NOT to Do

- Do NOT change `root: '.'` — it must stay as the debug-visualizer directory
- Do NOT add any proxy configuration — `/logs` is already a symlink in `public/`
- Do NOT remove `emptyOutDir: true` — production builds should clean the dist folder
- Do NOT change the port from 5173

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: Vite 6.x build
Acceptance_Criteria:
  - "npx vite build produces dist/ with both index.html and training/index.html (or training.html)"
  - "npm run dev serves both pages: / (playground) and /training.html (training)"
  - "Training page assets (CSS, JS) are correctly bundled"
  - "Playground page is unaffected by the config change"
Suggested_Test_Commands:
  - "cd debug-visualizer && npx vite build 2>&1 | tail -20"
  - "cd debug-visualizer && npx vite --port 5173"
Manual_Steps:
  - "Run build, check dist/ directory for both HTML files"
  - "Start dev server, open both URLs, verify both work"
```
