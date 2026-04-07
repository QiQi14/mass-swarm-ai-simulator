# Task J1: Split JS + CSS (Debug Visualizer)

- **Task_ID:** task_j1_split_js_css
- **Execution_Phase:** 1 (parallel)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files

### JS Draw Split
- `debug-visualizer/js/draw.js` → DELETE
- `debug-visualizer/js/draw/index.js` [NEW]
- `debug-visualizer/js/draw/entities.js` [NEW]
- `debug-visualizer/js/draw/terrain.js` [NEW]
- `debug-visualizer/js/draw/overlays.js` [NEW]
- `debug-visualizer/js/draw/effects.js` [NEW]
- `debug-visualizer/js/draw/fog.js` [NEW]

### JS Controls Split
- `debug-visualizer/js/controls.js` → DELETE
- `debug-visualizer/js/controls/index.js` [NEW]
- `debug-visualizer/js/controls/paint.js` [NEW]
- `debug-visualizer/js/controls/spawn.js` [NEW]
- `debug-visualizer/js/controls/zones.js` [NEW]
- `debug-visualizer/js/controls/split.js` [NEW]

### JS Panels Split
- `debug-visualizer/js/ui-panels.js` → DELETE
- `debug-visualizer/js/panels/index.js` [NEW]
- `debug-visualizer/js/panels/ml-panel.js` [NEW]
- `debug-visualizer/js/panels/zone-panel.js` [NEW]
- `debug-visualizer/js/panels/faction-panel.js` [NEW]

### CSS Split
- `debug-visualizer/style.css` → DELETE
- `debug-visualizer/css/variables.css` [NEW]
- `debug-visualizer/css/layout.css` [NEW]
- `debug-visualizer/css/panels.css` [NEW]
- `debug-visualizer/css/canvas.css` [NEW]
- `debug-visualizer/css/animations.css` [NEW]

### HTML Update
- `debug-visualizer/index.html` (update `<script>` and `<link>` imports)

## Dependencies
- None (Phase 1)

## Context_Bindings
- `context/conventions` (File Organization rules)

## Strict_Instructions

### Goal
Split oversized JS/CSS files into folder-based modules. **Pure refactor — zero logic changes.** The visualizer must render identically after the split.

### Step 1: Split `draw.js` (513 lines) → `js/draw/`

Create folder `js/draw/` with these files:

**`index.js`** — barrel exports:
```javascript
export { initCanvases, getCtx, getCanvasEntities, getScaleFactor, worldToCanvas, canvasToWorld, resizeCanvas } from './terrain.js';
export { drawEntities, getFactionColor } from './entities.js';
export { drawBackground } from './terrain.js';
export { drawFog } from './fog.js';
```

**`entities.js`** — Move:
- `getFactionColor()`
- `drawEntities()` (including health bar inline logic if tightly coupled)

**`terrain.js`** — Move:
- `initCanvases()`
- `getCtx()`, `getCanvasEntities()`, `getScaleFactor()`
- `worldToCanvas()`, `canvasToWorld()`
- `drawBackground()`
- `drawTerrain()` (private)
- `resizeCanvas()`

**`overlays.js`** — Move:
- `drawCoordinateGrid()`
- `drawSpatialGrid()`
- `drawFlowFieldArrows()`

**`effects.js`** — Move:
- `drawHealthBars()`
- `drawDeathAnimations()`

**`fog.js`** — Move:
- `drawFog()`

### Step 2: Split `controls.js` (398 lines) → `js/controls/`

**`index.js`** — barrel export of `initControls`:
```javascript
export { initControls } from './init.js';
```

**`init.js`** — keep `initControls()` and `clearModes()` (main setup)

**`paint.js`** — Move `addPaintCell()` and paint mode logic

**`spawn.js`** — Move `handleSpawnClick()` and spawn mode logic

**`zones.js`** — Move `handleZoneClick()` and zone mode logic

**`split.js`** — Move `handleSplitClick()`, `handleSelectClick()` and split/select mode logic

### Step 3: Split `ui-panels.js` (310 lines) → `js/panels/`

Split by panel concern. Each panel's show/hide/update logic in its own file.

### Step 4: Split `style.css` (777 lines) → `css/`

**`variables.css`** — CSS custom properties (`:root { --color-*, --size-*, etc. }`)

**`layout.css`** — Body, main grid, sidebar, toolbar layout rules

**`panels.css`** — All `.panel-*`, `.control-group`, `.ml-panel` styles

**`canvas.css`** — Canvas container, overlay, fog canvas styles

**`animations.css`** — `@keyframes`, transitions, hover effects

### Step 5: Update `index.html`

Replace single `<link>` with multiple CSS imports:
```html
<link rel="stylesheet" href="css/variables.css">
<link rel="stylesheet" href="css/layout.css">
<link rel="stylesheet" href="css/panels.css">
<link rel="stylesheet" href="css/canvas.css">
<link rel="stylesheet" href="css/animations.css">
```

Update `<script>` imports to use new paths:
```html
<script type="module" src="js/main.js"></script>
```
(main.js already imports from draw/controls — just update the import paths in main.js)

### Step 6: Delete original files

Delete `draw.js`, `controls.js`, `ui-panels.js`, `style.css`.

### Step 7: Verify

Open `debug-visualizer/index.html` in browser:
1. Canvas renders entities correctly
2. Terrain painting works
3. All control panels functional
4. CSS styling matches before/after
5. No console errors

## Verification_Strategy
  Test_Type: manual_steps
  Test_Stack: Browser
  Acceptance_Criteria:
    - "Every JS file under 200 lines"
    - "Every CSS file under 250 lines"
    - "Visualizer renders identically"
    - "All interactive modes work (paint, spawn, zone, split)"
    - "No browser console errors"
    - "index.html imports updated correctly"
  Manual_Steps:
    - "Open debug-visualizer/index.html in browser"
    - "Verify canvas renders entities"
    - "Test paint mode, spawn mode, zone mode"
    - "Verify all panels open/close correctly"
    - "Check browser console for import errors"
