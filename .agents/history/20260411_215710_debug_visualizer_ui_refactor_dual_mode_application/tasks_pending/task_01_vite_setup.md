# Task 01: Vite Setup & Project Restructure

## Task_ID
task_01_vite_setup

## Execution_Phase
Phase 1 (Parallel — no dependencies)

## Model_Tier
`advanced`

## Target_Files
- `debug-visualizer/package.json` — **NEW**
- `debug-visualizer/vite.config.js` — **NEW**
- `debug-visualizer/.gitignore` — **NEW**
- `debug-visualizer/src/config.js` — MOVE from `js/config.js`
- `debug-visualizer/src/state.js` — MOVE from `js/state.js`
- `debug-visualizer/src/websocket.js` — MOVE from `js/websocket.js`
- `debug-visualizer/src/draw/*` — MOVE from `js/draw/*`
- `debug-visualizer/src/controls/*` — MOVE from `js/controls/*`
- `debug-visualizer/src/main.js` — MOVE from `js/main.js`

## Dependencies
None.

## Context_Bindings
- `context/conventions` (JS file naming, module patterns)
- `context/architecture` (debug-visualizer folder structure)

## Strict_Instructions
See `implementation_plan_feature_1.md` → Task 01 for exhaustive step-by-step instructions.

Key steps:
1. Create `package.json` with Vite dev dependency
2. Create `vite.config.js` with `/logs` proxy to port 8080
3. Create `.gitignore` (node_modules, dist)
4. Move all JS files from `js/` → `src/`
5. Move all CSS files from `css/` → `src/styles/`
6. Update `index.html` to point to `src/main.js`
7. Create `public/` directory
8. Remove `js/training-overlay.js`
9. Verify: `npm install && npm run dev` must work

## Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser + Vite dev server
Acceptance_Criteria:
  - "npm run dev starts Vite dev server without errors"
  - "Browser opens and shows the existing visualizer UI"
  - "WebSocket connects to micro-core (green dot)"
  - "npm run build produces dist/ directory"
Manual_Steps:
  - "cd debug-visualizer && npm install && npm run dev"
  - "Verify canvas renders, sidebar appears, WS connects"
  - "npm run build — verify no build errors"
```

## Live_System_Impact
`safe`
