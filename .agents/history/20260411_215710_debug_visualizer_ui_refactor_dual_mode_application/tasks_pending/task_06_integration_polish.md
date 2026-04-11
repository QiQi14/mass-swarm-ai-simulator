# Task 06: Integration & Polish

## Task_ID
task_06_integration_polish

## Execution_Phase
Phase 4 (Depends on T04, T05)

## Model_Tier
`advanced`

## Target_Files
- `debug-visualizer/src/controls/init.js` — **REWRITE** (mode-aware, canvas-only)
- `debug-visualizer/src/main.js` — MODIFY (final wiring, remove workarounds)
- `debug-visualizer/src/websocket.js` — MODIFY (update imports to use new panel modules directly)
- `debug-visualizer/index.html` — MODIFY (remove legacy stubs)

## Dependencies
T04 (training panels exist), T05 (playground panels exist)

## Context_Bindings
- `context/conventions`
- `context/architecture`
- `skills/frontend-ux-ui` (design aesthetic — final polish, transitions, atmospheric effects)

## Strict_Instructions
See `implementation_plan_feature_2.md` → Task 06 for exhaustive instructions.

Key deliverables:
1. Rewrite `controls/init.js` — mode-aware, canvas events only (panel handlers bound in panels).
2. Final `main.js` wiring — import all CSS, panels, router, render loop with `updatePanels()`.
3. Update `websocket.js` — import `showToast` from components.
4. Cross-mode state persistence (clear spawn/paint modes on Training switch).
5. Clean up old `js/` and `css/` directories.
6. Full verification checklist (16 items).

---

### ⚠️ CRITICAL: T03 Workaround Cleanup (Post-T03 Adjustment)

T03 added several workarounds to keep the app running during the transition. **T06 must remove ALL of them:**

#### 1. Remove hidden canvas stubs from `index.html`
```html
<!-- REMOVE THIS BLOCK -->
<div style="display: none;">
    <canvas id="graph-tps" width="60" height="24"></canvas>
    <canvas id="graph-entities" width="60" height="24"></canvas>
</div>
```
These were added because the legacy `panels/index.js` (now rewritten by T04) referenced them. T04's new telemetry panel creates its own canvases.

#### 2. Remove `try/catch` around `initControls()` in `main.js`
```javascript
// REPLACE THIS:
try {
  initControls();
} catch(e) {
  console.warn('initControls partially failed...', e);
}

// WITH THIS:
initControls();
```
The rewritten `initControls()` should only handle canvas events + keyboard shortcuts (no DOM ID references that could fail).

#### 3. Remove `window.__sendCommand` global from `main.js`
```javascript
// REMOVE THIS LINE:
window.__sendCommand = sendCommand;
```
This was added for inline `onclick` handlers in `faction-panel.js`. After T04 rewrites the legend panel, this is no longer needed. All event handlers should use proper `addEventListener`.

#### 4. Remove null-guard toggle initialization from `main.js`
Lines 44-64 in current `main.js` check for toggle elements that don't exist. Remove these — they are now handled by T04's viewport panel.

#### 5. Update `websocket.js` imports
Currently imports from legacy path:
```javascript
// CHANGE FROM:
import { updatePerfBars, updateAggroGrid, updateLegend, updateMlBrainPanel, initFactionToggles } from './panels/index.js';

// CHANGE TO: import from the actual modules
import { updatePerfBars } from './panels/training/perf.js';
import { updateInspectorPanel, deselectEntity } from './panels/shared/inspector.js';
import { updateAggroGrid, updateLegend, initFactionToggles } from './panels/shared/legend.js';
import { updateMlBrainPanel } from './panels/training/ml-brain.js';
```
Then remove the backward-compat re-exports from `panels/index.js`.

#### 6. Delete legacy panel files
- `debug-visualizer/src/panels/faction-panel.js` — Replaced by `panels/shared/legend.js`
- `debug-visualizer/src/panels/ml-panel.js` — Replaced by `panels/training/ml-brain.js`
- `debug-visualizer/src/panels/zone-panel.js` — Empty placeholder, delete

#### 7. Rewrite `controls/init.js` (420 → ~80 lines)
The old `initControls()` is 420 lines that reference 40+ DOM IDs for panels, mode toggles, sliders, etc. After T04/T05, all panel-specific event handling is inside each panel's `render()`. The new `initControls()` should ONLY handle:
- Canvas mouse events (drag, pan, zoom, click-to-select/spawn/zone/split)
- Canvas wheel (zoom)
- Canvas dblclick (reset view)
- Keyboard shortcuts (if any)
- `clearModes()` function (null-safe: check element exists before accessing)

**DO NOT** bind any sidebar button events. Those are all panel-owned now.

## Verification_Strategy
```yaml
Test_Type: manual_steps + e2e
Test_Stack: Browser + running micro-core
Acceptance_Criteria:
  - "All 16 verification checklist items pass (see implementation_plan_feature_2.md)"
  - "No console errors"
  - "npm run build succeeds"
  - "Production build (dist/) serves correctly"
  - "No hidden stubs remain in index.html"
  - "No try/catch workarounds remain in main.js"
  - "No window.__sendCommand global"
  - "Legacy panel files (faction-panel.js, ml-panel.js, zone-panel.js) deleted"
Suggested_Test_Commands:
  - "cd debug-visualizer && npm run dev"
  - "cd micro-core && cargo run -- --smoke-test"
Manual_Steps:
  - "Full walkthrough of both modes"
  - "Switch between modes 10 times rapidly — no crashes"
  - "Connect to running micro-core, verify entities render"
  - "In Playground: spawn 500 entities, paint terrain, place zone"
  - "Switch to Training, verify training data, switch back, verify playground state persisted"
  - "View source of index.html — no hidden canvas stubs"
  - "Search codebase for window.__sendCommand — not found"
```

## Live_System_Impact
`safe`
