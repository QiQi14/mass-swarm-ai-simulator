# Task 14 Visualizer UI Changelog

## Touched Files
- `debug-visualizer/index.html`
- `debug-visualizer/visualizer.js`
- `debug-visualizer/style.css`

## Contract Fulfillment
- Implemented JS WebSocket interface handlers for sending `spawn_wave`, `set_terrain`, `clear_terrain`, `save_scenario`, `load_scenario`, and `set_fog_faction` commands.
- Implemented JS interface for reading incoming `SyncDelta` for visibility arrays (`visibility.explored`, `visibility.visible`).
- Implemented scenario file IO using dynamic download anchor generation and `FileReader` for JSON parsing.
- Refactored UI logic to use the new spawn coordinate calculations (`x`, `y` from `canvasToWorld`).
- Built Fog of War rendering overlay logic with `source-over` and `destination-out` compositing for black/translucent overlay on `offscreenCanvas` (`fogCanvas`).
- Built complete brush toolbar and paint-mode logic matching `BRUSH_MAP` constants and inverted integer costs for `hard_costs` (`65535` for walls, `200` for mud, `125` for pushable).

## Deviations/Notes
- Created `fogCanvas` (an off-screen canvas) dynamically in JS to hold the fog overlay rather than a fixed DOM element, compositing it using `destination-out` correctly so that explored areas are transparent and unexplored areas are solid black.
- Mapped `BRUSH_MAP` into an exact match of the core's `u16` scale.
- Bound `paintMode` effectively so dragging logic does NOT conflict with painting logic via a clear UI toggle.
- Added visual ghost rendering for Spawn Spread in `drawEntities`.
