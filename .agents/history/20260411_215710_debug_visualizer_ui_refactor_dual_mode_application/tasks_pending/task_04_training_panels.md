# Task 04: Training Mode Panels

## Task_ID
task_04_training_panels

## Execution_Phase
Phase 3 (Depends on T03)

## Model_Tier
`advanced`

## Target_Files
- `debug-visualizer/src/panels/index.js` — **REWRITE** (replace legacy code with panel registry + backward-compat re-exports)
- `debug-visualizer/src/panels/shared/telemetry.js` — **NEW**
- `debug-visualizer/src/panels/shared/inspector.js` — **NEW**
- `debug-visualizer/src/panels/shared/viewport.js` — **NEW**
- `debug-visualizer/src/panels/shared/legend.js` — **NEW**
- `debug-visualizer/src/panels/training/dashboard.js` — **NEW**
- `debug-visualizer/src/panels/training/ml-brain.js` — **NEW**
- `debug-visualizer/src/panels/training/perf.js` — **NEW**

## Dependencies
T03 (app shell exists, accordion component exists, sparkline component exists)

## Context_Bindings
- `context/conventions` (JS naming)
- `context/ipc-protocol` (WS message types for ML brain data)
- `skills/frontend-ux-ui` (design aesthetic — stat cards, dashboard layout)

## Strict_Instructions
See `implementation_plan_feature_2.md` → Task 04 for exhaustive instructions.

Key deliverables:
1. Panel Registry (`panels/index.js`) with `registerPanel()`, `addPanels()`, `renderAllPanels()`, `updatePanels()`.
2. Shared panels: Telemetry (TPS/tick sparklines), Inspector, Viewport layers, Legend.
3. Training panels: Dashboard (replaces training-overlay.js — CSV polling, win rate, reward chart), ML Brain status, Perf bars.

**IMPORTANT:** T05 will call `addPanels()` to register playground panels into this same registry. Export this function.

---

### ⚠️ CRITICAL: Legacy Code Reality (Post-T03 Adjustment)

**`panels/index.js` is NOT a blank file.** After T01 moved `js/` → `src/`, the old monolithic panel code now lives at `src/panels/index.js`. It contains legacy functions that `websocket.js` and `controls/init.js` actively import. **You MUST preserve backward-compatible exports** or the app will crash.

**Current legacy exports from `panels/index.js` that are actively imported:**

| Export | Imported By | What It Does |
|--------|------------|--------------|
| `Sparkline` (class) | (internal) | Canvas sparkline — references `#graph-tps`, `#graph-entities` via hidden HTML stubs |
| `sparklines` (object) | (internal) | Instances of Sparkline |
| `updatePerfBars(telemetry)` | `websocket.js` | Updates perf bar DOM from SyncDelta telemetry |
| `updateInspectorPanel()` | `controls/init.js` | Updates entity inspector DOM |
| `deselectEntity()` | `controls/init.js` | Clears entity selection |
| `startTelemetryLoop()` | (unused in current main.js) | 1-second interval updating TPS/entity counts |
| `updateAggroGrid()` | `websocket.js` (via re-export from `faction-panel.js`) | Updates aggro mask grid |
| `updateLegend()` | `websocket.js` (via re-export from `faction-panel.js`) | Updates faction legend |
| `initFactionToggles()` | `websocket.js` (via re-export from `faction-panel.js`) | Builds faction UI on WS connect |
| `updateMlBrainPanel()` | `websocket.js` (via re-export from `ml-panel.js`) | Updates ML brain status |

**Legacy source files also present:**
- `panels/faction-panel.js` — `updateAggroGrid()`, `updateLegend()`, `initFactionToggles()`
- `panels/ml-panel.js` — `updateMlBrainPanel()`, training status polling
- `panels/zone-panel.js` — empty placeholder

### Strategy: Rewrite + Backward-Compat Re-exports

1. **Rewrite `panels/index.js`** to be the proper panel registry (as described in the implementation plan).
2. **Move legacy function implementations INTO the new panel modules** where they belong:
   - `updatePerfBars()` → `panels/training/perf.js`
   - `updateInspectorPanel()` / `deselectEntity()` → `panels/shared/inspector.js`
   - `updateAggroGrid()` → `panels/shared/legend.js` or a new shared aggro panel 
   - `updateLegend()` / `initFactionToggles()` → `panels/shared/legend.js`
   - `updateMlBrainPanel()` → `panels/training/ml-brain.js`
   - `startTelemetryLoop()` → `panels/shared/telemetry.js`
   - `Sparkline` class → replaced by `components/sparkline.js` (already created by T03)
3. **Re-export all legacy function names from `panels/index.js`** so `websocket.js` and `controls/init.js` can continue importing them unchanged. Example:
   ```javascript
   // ─── Panel Registry ──────────────────────────────────────────
   // ... (new registry code) ...

   // ─── Backward-compat re-exports (consumed by websocket.js, controls/init.js) ───
   // These will be cleaned up in T06 when websocket.js is updated.
   export { updatePerfBars } from './training/perf.js';
   export { updateInspectorPanel, deselectEntity } from './shared/inspector.js';
   export { updateAggroGrid, updateLegend, initFactionToggles } from './shared/legend.js';
   export { updateMlBrainPanel } from './training/ml-brain.js';
   ```
4. **DO NOT delete `panels/faction-panel.js` or `panels/ml-panel.js`** — T06 will clean them up. But their logic should be absorbed into the new modules.

### Panel Rendering Notes
- Each panel module should create its own DOM elements in `render(body)`. Do NOT reference DOM IDs that are hardcoded in index.html — they don't exist.
- The telemetry panel should create sparkline canvases dynamically and use the `drawSparkline()` function from `components/sparkline.js` (created by T03).
- The inspector panel should create its DOM structure in `render()`, then `update()` populates it from `state.selectedEntityId`.

## Verification_Strategy
```yaml
Test_Type: manual_steps
Test_Stack: Browser
Acceptance_Criteria:
  - "In Training Mode: Dashboard, ML Brain, Telemetry, Perf, Viewport, Legend panels visible"
  - "Dashboard shows episode count, win rate, reward chart (mock or real data)"
  - "Shared panels (Telemetry, Viewport) visible in both modes"
  - "Inspector auto-expands when entity selected"
  - "Accordion expand/collapse works smoothly"
  - "No console errors from websocket.js importing legacy functions"
  - "WS connect still triggers initFactionToggles() without crash"
Manual_Steps:
  - "Switch to Training mode → verify all training panels appear"
  - "Click entity on canvas → verify inspector expands"
  - "Collapse/expand panels → verify smooth animation"
  - "Check browser console — no import/reference errors from panels/index.js"
```

## Live_System_Impact
`safe`
