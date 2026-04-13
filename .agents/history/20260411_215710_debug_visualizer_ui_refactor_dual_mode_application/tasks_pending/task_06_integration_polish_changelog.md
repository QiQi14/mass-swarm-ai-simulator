# Target Task: task_06_integration_polish

## Touched Files
- `debug-visualizer/src/main.js` (MODIFIED)
- `debug-visualizer/src/controls/init.js` (MODIFIED)
- `debug-visualizer/src/websocket.js` (MODIFIED)
- `debug-visualizer/src/panels/index.js` (MODIFIED)
- `debug-visualizer/index.html` (MODIFIED)
- `debug-visualizer/src/panels/faction-panel.js` (DELETED)
- `debug-visualizer/src/panels/ml-panel.js` (DELETED)
- `debug-visualizer/src/panels/zone-panel.js` (DELETED)

## Contract Fulfillment
- Fully rewrote `controls/init.js` with mode-aware safe logic holding strictly to canvas mouse/wheel event handling. Null-safe mode cleanup included.
- Finalized wiring in `main.js` which drops try/catch and global stubs. Configured the main frame loop (`updatePanels()`) and the unified mode/scroll containers.
- Re-routed WebSocket handler bindings correctly in `websocket.js` mapping straight into explicit inner file module scopes. Cleaned up `panels/index.js` to prevent double bindings.
- Successfully purged deprecated legacy layout files, stubs, and empty components resolving backwards compatibility overlaps.

## Deviations/Notes
- The prompt explicitly tasked rewriting `main.js` which introduced legacy `import { initControls } from './controls/init.js'` rather than index.js, this was properly routed.
- `websocket.js` required pointing specific functional binds straight to their concrete implementation locations (`panels/training/perf.js` etc) skipping the central index pattern as required by the instruction constraint to bypass redundant logic.

## Human Interventions
- None.
