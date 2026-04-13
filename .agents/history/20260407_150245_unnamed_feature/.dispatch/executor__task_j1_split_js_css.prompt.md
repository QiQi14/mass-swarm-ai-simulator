# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_j1_split_js_css` |
| Feature | Unnamed Feature |
| Tier    | standard |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_j1_split_js_css_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_j1_split_js_css
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `basic`:**
- Skip all external file reading. Your Task Brief below IS your complete instruction.
- Implement the code exactly as specified in the Task Brief.
- Follow the MANDATORY PROCESS rules above (changelog + scope), then halt.

**If your tier is `standard` or `advanced`:**
1. Read `.agents/context.md` — Thin index pointing to context sub-files
2. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
3. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
4. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
5. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

_No additional context bindings specified._

---

## Task Brief

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

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

