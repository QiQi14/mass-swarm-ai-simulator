# Research Digest: Training Page Fullscreen Overlay Redesign

> **Strategist → Planner handoff artifact**
> Structured codebase facts extracted during the strategy phase.
> The Planner should use this instead of re-reading source files.

---

## 1. Current File Inventory

### Entry Points

| File | Purpose | Lines |
|------|---------|-------|
| `debug-visualizer/index.html` | Single HTML entry, contains `#app > .canvas-area + .sidebar` | 52 |
| `debug-visualizer/src/main.js` | Boots router, tabs, panels, canvas, WS, render loop | 71 |
| `debug-visualizer/vite.config.js` | Vite dev server config | ~15 |

### Router

| File | Key Exports |
|------|-------------|
| `src/router.js` | `MODES { TRAINING, PLAYGROUND }`, `getCurrentMode()`, `setMode(mode)`, `onModeChange(cb)`, `initRouter()` |

- Hash-based routing: `#training` or `#playground`
- Default mode: `PLAYGROUND`
- Listeners array notified on mode change

### State Module

| File | Key Exports |
|------|-------------|
| `src/state.js` | `entities`, `flowFieldCache`, `selectedEntityId`, `currentTick`, `ws`, `mlBrainStatus`, `arenaBounds`, `viewX/Y/Scale`, 30+ flags |

- ES module singleton pattern — one instance per page load
- No mutable shared state across pages (each import creates a fresh module graph)

### Panel System

| File | Key Exports |
|------|-------------|
| `src/panels/index.js` | `registerPanel(panel)`, `renderAllPanels(container)`, `onModeSwitch(container, mode)`, `updatePanels()` |

Panel registration order (matters for rendering):
1. `dashboardPanel` (training)
2. `mlBrainPanel` (training)
3. `telemetryPanel` (training + playground)
4. `perfPanel` (training)
5. `viewportPanel` (shared)
6. `inspectorPanel` (shared)
7. `legendPanel` (shared)
8. 8× playground panels

Panel interface contract:
```js
{
  id: string,
  title: string,
  icon: string,
  modes: string[],     // ['training'] or ['playground'] or ['training','playground']
  defaultExpanded: boolean,
  render(body: HTMLElement): void,
  update?(): void,      // called every frame if mode matches
  _accordionRef?: { element, body, setExpanded }  // set by registry
}
```

### Training Panels

| File | Data Source | Update Mechanism |
|------|-----------|-----------------|
| `panels/training/dashboard.js` | HTTP poll `/logs/run_latest/training_status.json` | 5s/30s adaptive polling (internal setInterval) |
| `panels/training/ml-brain.js` | WS `msg.ml_brain` field via `state.mlBrainStatus` | Per-frame `update()` + direct call from websocket.js |
| `panels/training/perf.js` | WS `msg.telemetry` field | Direct call from `websocket.js → updatePerfBars()` |

### Shared Panels Used by Training

| File | Data Source |
|------|-----------|
| `panels/shared/telemetry.js` | `state.entities`, `state.currentTick`, `state.tpsCounter` (1s interval) |
| `panels/shared/inspector.js` | `state.selectedEntityId` → entity lookup |
| `panels/shared/viewport.js` | Layer toggle checkboxes |
| `panels/shared/legend.js` | `state.activeSubFactions`, `state.aggroMasks` |

### Canvas Drawing Pipeline

| File | Exports |
|------|---------|
| `src/draw/index.js` | `initCanvases()`, `resizeCanvas()`, `drawEntities()`, `drawFog()`, `drawBackground()`, `drawArenaBounds()` |
| `src/draw/entities.js` | Entity rendering with faction colors |
| `src/draw/fog.js` | Fog-of-war overlay |
| `src/draw/terrain.js` | Terrain cost visualization |
| `src/draw/overlays.js` | Flow field, density, ECP overlays |
| `src/draw/effects.js` | Death animations |

Two canvas layers:
- `#canvas-bg` (z-index 1): background, grid, terrain
- `#canvas-entities` (z-index 2): entities, effects, cursor interaction

### WebSocket Module

| File | Key Functions |
|------|---------------|
| `src/websocket.js` | `connectWebSocket()`, `sendCommand(cmd, params)` |

Connects to `ws://<hostname>:8080`. Handles message types:
- `SyncDelta` — entities (moved/removed), telemetry, fog, zone_modifiers, ml_brain, density
- `FlowFieldSync` — flow field vectors
- `scenario_data` — downloads scenario JSON

Direct imports from panels (tight coupling):
- `updatePerfBars` from `training/perf.js`
- `updateAggroGrid`, `updateLegend`, `initFactionToggles` from `shared/legend.js`
- `updateMlBrainPanel` from `training/ml-brain.js`

### CSS Architecture

| File | Scope |
|------|-------|
| `styles/variables.css` | CSS custom properties (colors, fonts, spacing, sizing) |
| `styles/reset.css` | Browser reset |
| `styles/layout.css` | `.app-container`, `.canvas-area`, `.sidebar`, `.tab-bar`, `.panel-scroll`, `.connection-badge`, mobile bottom-sheet |
| `styles/panels.css` | `.panel-group`, `.stat-grid`, `.stat-card`, `.faction-list`, `.inspector-*` |
| `styles/canvas.css` | Canvas-specific styles |
| `styles/controls.css` | Form controls, buttons, inputs |
| `styles/training.css` | `.training-dashboard`, `.stage-badge`, `.streak-badge`, `.win-rate-*`, `.perf-bar-*` |
| `styles/animations.css` | Keyframe animations |

Key CSS variables:
- `--sidebar-width: 380px`
- `--bg-surface: rgba(8, 12, 18, 0.92)` — glass-ready base
- `--accent-primary: #06d6a0` — teal/cyan accent
- `--font-display: 'Geist'` / `--font-mono: 'Geist Mono'`

### Component Library

| File | Purpose |
|------|---------|
| `components/accordion.js` | `createAccordion(opts)`, `applyModeFilter(container, mode)` |
| `components/tabs.js` | `renderTabs()`, `updateTabs()` — Training/Playground tab bar |
| `components/sparkline.js` | `drawSparkline(canvas, data, opts)` — inline mini charts |
| `components/bottom-sheet.js` | Mobile swipe-up sheet |
| `components/toast.js` | Toast notification |

### Training Curriculum Data

Located at: `macro-brain/profiles/tactical_curriculum.json`

Key sections for the stage info card:
```json
{
  "training.curriculum[N]": {
    "stage": N,
    "description": "...",
    "graduation": { "win_rate": 0.80, "min_episodes": 50 }
  },
  "combat.rules[]": [
    { "source_faction": 0, "target_faction": 1, "range": 25.0,
      "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }] }
  ],
  "actions[]": [
    { "index": 0, "name": "Hold", "unlock_stage": 0 }
  ],
  "factions[]": [
    { "id": 0, "name": "Brain", "role": "brain", "stats": { "hp": 100 } }
  ]
}
```

### Vite Configuration

```js
// Current vite.config.js
import { defineConfig } from 'vite';
export default defineConfig({
  server: {
    proxy: {
      '/logs': 'http://localhost:8080',
    },
  },
});
```

Needs multi-page input configuration for `training.html` + `index.html`.

---

## 2. Integration Points & Gotchas

### WebSocket Tight Coupling

`websocket.js` directly imports and calls panel update functions:
```js
import { updatePerfBars } from './panels/training/perf.js';
import { updateAggroGrid, updateLegend, initFactionToggles } from './panels/shared/legend.js';
import { updateMlBrainPanel } from './panels/training/ml-brain.js';
```

**Gotcha:** The training page's `websocket.js` import graph MUST include these panel modules, or imports will fail. For the new overlay system, either:
- Keep the same import pattern (panels just render differently)
- Refactor to an event/pub-sub pattern (cleaner but more work)

### Training Status HTTP Polling

`dashboard.js` polls `/logs/run_latest/training_status.json` via fetch. This path is proxied by Vite (`/logs → http://localhost:8080`). The new training page must maintain this proxy.

Expected response shape:
```json
{
  "stage": 1,
  "episode": 659,
  "win_rate": 0.50,
  "grad_streak": 0
}
```

### Canvas Hint Reference

The connection badge (`#connection-badge`) and canvas hint (`#canvas-hint`) are positioned absolutely within `.canvas-area`. They'll work fine in fullscreen mode since `.canvas-area` already uses `position: relative`.

### Render Loop

```js
function renderFrame() {
  ctx.clearRect(0, 0, ...);
  drawEntities();
  if (S.showFog) drawFog();
  drawArenaBounds(ctx);
  updatePanels();  // per-frame panel updates
  requestAnimationFrame(renderFrame);
}
```

`updatePanels()` iterates all registered panels and calls `update()` if the panel's mode matches. For the new training page, this needs to only call training-mode panels.

### Auto Arena Bounds Detection

`websocket.js` has `autoDetectArenaBounds()` that updates `arenaBounds` state and tries to set `#arena-width` / `#arena-height` input elements. These inputs only exist in playground mode. The training page should not break if these elements are missing (and they won't — querySelector returns null, the assignment is guarded by `if (wInput)`).

---

## 3. Files That Need Modification

| File | Change Type | Reason |
|------|-------------|--------|
| `training.html` | **NEW** | New entry point with fullscreen overlay DOM |
| `src/training-main.js` | **NEW** | Training-specific bootstrap (no playground panels, no sidebar) |
| `src/panels/training/stage-info.js` | **NEW** | Stage goal + ruleset overlay card |
| `src/styles/overlay.css` | **NEW** | Glassmorphic overlay card styles, minimize animation |
| `vite.config.js` | **MODIFY** | Add multi-page rollup input |
| `index.html` | **MODIFY** | Potentially rename or update navigation |
| `src/websocket.js` | **MINOR** | Decouple panel imports (optional, can keep as-is) |

---

## 4. Data Flow for Stage Info Card

```
training-main.js boot
  → fetch('/profiles/tactical_curriculum.json')
  → store in state or module-level variable
  
Training status poll (every 5s)
  → GET /logs/run_latest/training_status.json
  → returns { stage: N, episode, win_rate, grad_streak }
  
Stage info card render:
  → curriculum.training.curriculum[N].description  → "Goal" text
  → curriculum.training.curriculum[N].graduation   → "Graduate at 80% WR, min 50 eps"
  → curriculum.actions.filter(a => a.unlock_stage <= N) → "Unlocked actions" list
  → curriculum.combat.rules                        → "Combat rules" table
  → curriculum.factions                            → faction names for rules display
```

The curriculum JSON is static per session. The stage index is dynamic from the poll.
