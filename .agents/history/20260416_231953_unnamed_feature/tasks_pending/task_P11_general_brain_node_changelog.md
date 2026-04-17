# Changelog: task_P11_general_brain_node

## Touched Files
- `debug-visualizer/package.json`
- `debug-visualizer/src/node-editor/nodes/general.js`
- `debug-visualizer/src/node-editor/brain-runner.js`
- `debug-visualizer/src/node-editor/compiler.js`

## Contract Fulfillment
- Added `onnxruntime-web` dependency to `package.json`.
- Created `general.js` node UI rendering, providing model selection, interval range input, and mode toggle for ONNX.js.
- Implemented `brain-runner.js` containing `startBrainRunner`, responsible for tracking interval ticks, loading `.onnx` models, performing inference against `S.mlBrainStatus.observation`, and outputting directives via `sendCommand('inject_directive')`.
- Extended `compiler.js` to isolate `brains` configs, bypassing standard Navigation node serialization if a `General` node operates on the same faction, and executing Phase 5 (Brain Init).

## Deviations/Notes
- `mlBrainStatus` fetching relies functionally on the engine passing observation grids to `S.mlBrainStatus.observation` directly.
- Python ZMQ mode logs a console warning as its backend bridge is designated for future enhancement integration.
- The decoding logic in `brain-runner.js` applies an abstracted mapping for the 8-state `MultiDiscrete` policy; precise action parameters (x, y coords, specific target bindings) may require calibration relative to the active ONNX model's structure.
