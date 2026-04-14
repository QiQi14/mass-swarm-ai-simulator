# Task 03: Training Entry Point + Overlay Renderer + Mobile Sheet

## Metadata

```yaml
Task_ID: task_03_training_entry
Execution_Phase: 2
Model_Tier: advanced
Live_System_Impact: safe
Feature: "Training Page — Fullscreen Map + Overlay Dashboard Redesign"
```

## Target_Files

- `debug-visualizer/training.html` [NEW]
- `debug-visualizer/src/training-main.js` [NEW]

## Dependencies

- Task 01 (`src/styles/overlay.css` must exist)
- Task 02 (`src/panels/training/stage-info.js` must exist)

## Context_Bindings

- `skills/frontend-ux-ui`
- `strategy_brief.md`
- `research_digest.md`

## Strict_Instructions

Create the Training page entry point (`training.html`) and its JavaScript bootstrap (`training-main.js`). This is the core assembly task that wires together the overlay CSS (Task 01), the stage info panel (Task 02), and all existing training/shared panels into a fullscreen map with floating overlay dashboard.

### File 1: `training.html`

New HTML entry point. Must be placed at the project root of `debug-visualizer/` (same level as `index.html`).

**Structure:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SwarmControl — Training</title>
    <meta name="description" content="Training dashboard for the Mass-Swarm AI Simulator">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
</head>
<body class="training-page">
    <!-- Fullscreen Canvas -->
    <main class="canvas-area" id="canvas-area">
        <canvas id="canvas-bg"></canvas>
        <canvas id="canvas-entities"></canvas>
        <div class="canvas-hint" id="canvas-hint">
            Pan: drag · Zoom: scroll · Double-click: reset view
        </div>
    </main>

    <!-- Overlay Root -->
    <div id="overlay-root" class="overlay--expanded">
        <!-- Top Bar -->
        <div class="overlay-top-bar" id="overlay-top-bar">
            <!-- Built by training-main.js -->
        </div>

        <!-- Desktop Overlay Card Groups -->
        <div class="overlay-group--left" id="overlay-left"></div>
        <div class="overlay-group--right" id="overlay-right"></div>

        <!-- Minimized Strip -->
        <div class="overlay-mini-strip" id="overlay-mini-strip"></div>
    </div>

    <!-- Layers Dropdown (desktop) -->
    <div class="layers-dropdown" id="layers-dropdown"></div>

    <!-- Mobile Training Sheet -->
    <div class="training-sheet" id="training-sheet">
        <div class="training-sheet__handle"><div class="handle-pill"></div></div>
        <div class="training-sheet__peek" id="training-sheet-peek"></div>
        <div class="training-sheet__body" id="training-sheet-body"></div>
    </div>

    <script type="module" src="/src/training-main.js"></script>
</body>
</html>
```

**Critical rules:**
- `<body class="training-page">` — used by overlay.css to scope training-specific rules
- Canvas area is NOT wrapped in `.app-container` — it fills the viewport
- Canvas area uses inline `style="width:100vw;height:100vh;"` (or rely on overlay.css to set it)
- Connection badge elements (`#connection-badge`, `#status-dot`, `#status-text`) are built by JS in the top bar — `websocket.js` queries these IDs so they must exist by the time WS connects
- NO sidebar element, NO `.app-container`, NO tab bar, NO panel-scroll
- NO `#arena-width` or `#arena-height` inputs — those are playground-only. `websocket.js` safely guards these with `if (wInput)` checks.

### File 2: `training-main.js`

Training-specific entry point. Target ~250 lines.

#### CSS Imports

```js
import './styles/reset.css';
import './styles/variables.css';
import './styles/canvas.css';
import './styles/panels.css';     // stat-grid, stat-card classes used by panel renders
import './styles/controls.css';   // toggle-control used by viewport panel
import './styles/training.css';   // training-dashboard, stage-badge, win-rate classes
import './styles/overlay.css';    // NEW overlay system (Task 01)
```

> **DO NOT import `layout.css`** — it defines the sidebar/flex-row layout which is not used here. `overlay.css` provides the training page's own layout.

> **DO NOT import `animations.css`** unless specific keyframes from it are needed — overlay.css has its own animations.

#### Module Imports

```js
import * as S from './state.js';
import { connectWebSocket } from './websocket.js';
import { initCanvases, resizeCanvas, drawEntities, drawFog, drawBackground, drawArenaBounds } from './draw/index.js';
import { initControls } from './controls/init.js';

// Training panels
import dashboardPanel from './panels/training/dashboard.js';
import mlBrainPanel from './panels/training/ml-brain.js';
import perfPanel from './panels/training/perf.js';
import stageInfoPanel, { loadCurriculum } from './panels/training/stage-info.js';

// Shared panels (needed for training mode)
import telemetryPanel from './panels/shared/telemetry.js';
import viewportPanel from './panels/shared/viewport.js';

// Legend must be imported for websocket.js side-effect coupling
import './panels/shared/legend.js';
// Inspector imported for entity click
import './panels/shared/inspector.js';
```

**Why legend.js and inspector.js are imported:** `websocket.js` directly imports `updateAggroGrid`, `updateLegend`, `initFactionToggles` from `legend.js` and the module graph must resolve. Similarly, `inspector.js` registers with the panel system. They are imported as side-effects only — their UI is NOT rendered as overlay cards.

#### Boot Sequence

```js
// 1. Canvas init
const bgCanvas = document.getElementById('canvas-bg');
const canvasEntities = document.getElementById('canvas-entities');
initCanvases(bgCanvas, canvasEntities);

// 2. Load curriculum data
loadCurriculum();

// 3. Build overlay UI
buildTopBar();
renderOverlayCards();
initOverlayToggle();
initLayersDropdown();
initMobileSheet();

// 4. Canvas controls
initControls();

// 5. Connect and render
window.addEventListener('resize', resizeCanvas);
resizeCanvas();
connectWebSocket();
requestAnimationFrame(renderFrame);
```

#### `buildTopBar()` Function

Populates `#overlay-top-bar` with:

```html
<div class="overlay-top-bar__left">
  <div class="connection-badge" id="connection-badge">
    <div class="status-dot" id="status-dot"></div>
    <span id="status-text">Connecting…</span>
  </div>
  <span class="overlay-top-bar__title">Swarm<span style="color:var(--text-accent)">Control</span></span>
  <span class="stage-badge" id="topbar-stage">Stage ?</span>
</div>
<div class="overlay-top-bar__actions">
  <button class="overlay-btn" id="overlay-minimize-btn" title="Minimize dashboard">
    <span>—</span>
  </button>
  <button class="overlay-btn" id="overlay-layers-btn" title="Toggle layer controls">
    <span>👁</span>
  </button>
</div>
```

**Important:** `#connection-badge`, `#status-dot`, `#status-text` are placed HERE in the top bar. `websocket.js` uses `document.getElementById()` to find these — they MUST have these exact IDs.

#### `renderOverlayCards()` Function

Panel position map:
```js
const PANEL_LAYOUT = {
  'stage-info':  { group: 'left',  panel: stageInfoPanel },
  'dashboard':   { group: 'left',  panel: dashboardPanel },
  'ml-brain':    { group: 'left',  panel: mlBrainPanel },
  'telemetry':   { group: 'right', panel: telemetryPanel },
  'perf':        { group: 'right', panel: perfPanel },
};
```

For each entry:
1. Create `.overlay-card` element
2. Create `.overlay-card__header` with icon + title
3. Create `.overlay-card__body` div
4. Call `panel.render(cardBody)` to populate
5. Store reference: `panel._overlayRef = { element, body }`
6. Append to `#overlay-left` or `#overlay-right` based on group

#### `initOverlayToggle()` Function

```js
function initOverlayToggle() {
  const root = document.getElementById('overlay-root');
  const btn = document.getElementById('overlay-minimize-btn');
  
  // Restore persisted state
  const stored = localStorage.getItem('overlay-minimized');
  if (stored === 'true') {
    root.classList.replace('overlay--expanded', 'overlay--minimized');
    btn.innerHTML = '<span>□</span>';
  }
  
  btn.addEventListener('click', () => {
    const isMinimized = root.classList.contains('overlay--minimized');
    if (isMinimized) {
      root.classList.replace('overlay--minimized', 'overlay--expanded');
      btn.innerHTML = '<span>—</span>';
      localStorage.setItem('overlay-minimized', 'false');
    } else {
      root.classList.replace('overlay--expanded', 'overlay--minimized');
      btn.innerHTML = '<span>□</span>';
      localStorage.setItem('overlay-minimized', 'true');
    }
  });
}
```

#### `initLayersDropdown()` Function

- Renders `viewportPanel.render(dropdownBody)` into `#layers-dropdown`
- Toggle via `#overlay-layers-btn` click
- Adds/removes `.layers-dropdown--open` class
- Click-outside detection: `document.addEventListener('click', ...)` with `event.target.closest()` check
- Fog toggles from `viewportPanel` are included automatically

#### `initMobileSheet()` Function

Mobile bottom sheet with swipe gestures. Only functional at `≤ 768px`.

**Peek bar content** (`#training-sheet-peek`):
```html
<span class="mini-strip__stage" id="mobile-stage">Stage ?</span>
<span class="mini-strip__metric" id="mobile-ep">EP 0</span>
<span class="mini-strip__metric" id="mobile-wr">0%</span>
```

**Expanded body content** (`#training-sheet-body`):
1. Training status summary card (reads from dashboard DOM values — same pragmatic coupling as stage-info)
2. Viewport layer toggles — render `viewportPanel.render(layerContainer)` into the body

**Swipe gesture:**
```js
let touchStartY = 0;
const sheet = document.getElementById('training-sheet');
const handle = sheet.querySelector('.training-sheet__handle');

handle.addEventListener('touchstart', (e) => {
  touchStartY = e.changedTouches[0].screenY;
}, { passive: true });

handle.addEventListener('touchend', (e) => {
  const delta = e.changedTouches[0].screenY - touchStartY;
  if (delta < -50) sheet.classList.add('training-sheet--expanded');
  else if (delta > 50) sheet.classList.remove('training-sheet--expanded');
}, { passive: true });

// Also toggle on handle click
handle.addEventListener('click', () => {
  sheet.classList.toggle('training-sheet--expanded');
});
```

#### `renderFrame()` Function

```js
function renderFrame() {
  const ctx = canvasEntities.getContext('2d');
  ctx.clearRect(0, 0, canvasEntities.width, canvasEntities.height);
  drawEntities();
  if (S.showFog) drawFog();
  drawArenaBounds(ctx);
  updateOverlayPanels();
  requestAnimationFrame(renderFrame);
}
```

#### `updateOverlayPanels()` Function

```js
function updateOverlayPanels() {
  // Update each panel that has an update() method
  for (const { panel } of Object.values(PANEL_LAYOUT)) {
    if (panel.update) panel.update();
  }
  // Update mini-strip
  updateMiniStrip();
  // Update mobile peek bar
  updateMobilePeek();
  // Update topbar stage badge
  updateTopbarStage();
}
```

#### `updateMiniStrip()` Function

Reads values from dashboard DOM and updates `#overlay-mini-strip` content:
- Stage badge from `#dash-stage`
- Episode from `#dash-ep`
- Win rate from `#dash-wr`
- Connection status from `#status-dot` class

#### `updateMobilePeek()` Function

Same data as mini-strip but writes to `#mobile-stage`, `#mobile-ep`, `#mobile-wr`.

#### `updateTopbarStage()` Function

Reads `#dash-stage` and updates `#topbar-stage` text content.

### What NOT to Do

- Do NOT import `layout.css` — it defines sidebar layout
- Do NOT import `router.js` — this page IS training mode, no routing needed
- Do NOT import playground panels (`game-setup.js`, `sim-controls.js`, `spawn.js`, `terrain.js`, `zones.js`, `splitter.js`, `aggro.js`, `behavior.js`)
- Do NOT import `components/tabs.js` or `components/bottom-sheet.js` — those are for the playground sidebar
- Do NOT import `components/accordion.js` — overlay cards are not accordions
- Do NOT create or modify any file outside of `training.html` and `training-main.js`
- Do NOT delete or modify `index.html` or `main.js`
- Do NOT use the `panels/index.js` registry — the overlay system manages its own panel rendering

### Known Integration Points

1. **`websocket.js` tight coupling:** This module imports `updatePerfBars` from `perf.js`, `updateMlBrainPanel` from `ml-brain.js`, and `updateAggroGrid`/`updateLegend`/`initFactionToggles` from `legend.js`. The training page MUST import these modules to avoid broken module graph. Legend and inspector are imported as side-effects only.

2. **`controls/init.js`:** Uses `document.getElementById()` for spawn/zone/split/paint buttons — these don't exist on the training page. The code is already null-guarded (`if (spawnBtn)`, etc.), so no crash.

3. **`autoDetectArenaBounds()` in websocket.js:** Tries to set `#arena-width` / `#arena-height` input values. Already null-guarded: `if (wInput) wInput.value = ...`. Safe.

4. **Canvas hint:** Has class `canvas-hint` and ID `canvas-hint`. Overlay.css (Task 01) hides it by default on `.training-page` and shows it only when `.overlay--minimized` is active.

## Verification_Strategy

```yaml
Test_Type: manual_steps
Test_Stack: Browser (Chrome/Firefox)
Acceptance_Criteria:
  - "training.html loads with fullscreen canvas and NO sidebar"
  - "Top bar shows connection badge, title, stage badge, minimize and layers buttons"
  - "5 overlay cards render in correct groups (3 left, 2 right)"
  - "Panels update with live data when Rust core is running"
  - "Minimize toggle: cards hide, mini-strip appears, canvas hint shows"
  - "Expand toggle: cards slide back in, mini-strip hides, hint hides"
  - "Minimize state persists across page reload via localStorage"
  - "Layers button opens dropdown with all viewport toggles"
  - "Dropdown closes on click-outside"
  - "Mobile (375px): sheet peek bar shows, swipe up expands to status + layers"
  - "Playground page (index.html) is completely unaffected"
  - "No console errors on page load or during WS connection"
Manual_Steps:
  - "Open http://localhost:5173/training.html — verify fullscreen map"
  - "Verify 5 overlay cards (Stage Info, Dashboard, ML Brain left; Telemetry, Perf right)"
  - "Click minimize — verify mini-strip and canvas hint"
  - "Click expand — verify cards return"
  - "Refresh — verify minimize state persisted"
  - "Click layers icon — verify dropdown with toggles"
  - "Use Chrome DevTools responsive mode (375px) — verify mobile sheet"
  - "Open http://localhost:5173/ — verify playground unchanged"
```
