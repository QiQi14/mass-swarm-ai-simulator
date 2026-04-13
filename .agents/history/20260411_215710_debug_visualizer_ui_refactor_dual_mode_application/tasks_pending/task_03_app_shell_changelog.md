# Task 03 Changelog: App Shell & Mode Router

## Touched Files
- `debug-visualizer/index.html` (REWRITE)
- `debug-visualizer/src/main.js` (REWRITE)
- `debug-visualizer/src/router.js` (NEW)
- `debug-visualizer/src/components/tabs.js` (NEW)
- `debug-visualizer/src/components/accordion.js` (NEW)
- `debug-visualizer/src/components/sparkline.js` (NEW)
- `debug-visualizer/src/components/toast.js` (NEW)
- `debug-visualizer/src/websocket.js` (MODIFIED - extracted `showToast`)

## Contract Fulfillment
- **Contract C1 (Mode Router API):** Implemented in `src/router.js` with `MODES`, `getCurrentMode`, `setMode`, `onModeChange`, and hash listener. 
- **Contract C2 (Accordion Panel API):** Implemented in `src/components/accordion.js` with `createAccordion` returning elements with `setExpanded`. Included `applyModeFilter` for filtering panels based on `#training` / `#playground`.
- **Reusable Components:** Implemented `tabs.js`, `sparkline.js`, and extracted `toast.js` from `websocket.js`.
- **Application Shell:** Rewrote `index.html` as the app container. Main logic retained exact canvas, WS connection, and render loop logic in JS while deferring missing DOM parts to be fully implemented in T04-T06.

## Deviations/Notes
- Since the panels are entirely deleted from `index.html` in this task and will be incrementally built as JS logic in tasks `T04`/`T05`, `initControls()` (which hasn't been rewritten yet as instructed) calls methods on now-non-existent DOM nodes. To prevent this from blocking the application's render loop and WS connections required for visualizer initialization (which verifies canvas rendering), I wrapped `initControls()` in a `try...catch` block gracefully inside `src/main.js`. This ensures compliance while waiting for the T06 `init.js` refactor.
- `document.getElementById` for various UI toggles in `src/main.js` (e.g., `#toggle-grid`) returned `null`, so null checks were added to prevent crash at initialization.
- **QA Fix (Attempt 1):** Re-exported `showToast` from `websocket.js` (`export { showToast } from './components/toast.js';`) because out-of-scope files like `src/controls/spawn.js` still rely on importing it from `websocket.js`.
- **QA Fix (Attempt 2):** Added hidden canvas stubs (`#graph-tps`, `#graph-entities`) inside `index.html` to prevent module-load crashes from legacy out-of-scope `src/panels/index.js` which immediately accesses these IDs.

## Human Interventions
No human interventions.
