# Strategy Brief: Training Page — Fullscreen Map + Overlay Dashboard Redesign

## Problem Statement

The current Debug Visualizer uses a single side panel (380px) to display **all** training information and playground controls via tab switching. This creates two problems:

1. **Space crunch** — Training dashboard, ML brain, telemetry, and performance panels are crammed into a narrow sidebar, making the UI feel unprofessional and data-dense.
2. **Single-page lock** — Training and playground share the same canvas/sidebar, preventing users from monitoring training while simultaneously playing in the playground (you can only do one or the other).

The user wants a **premium command-center aesthetic** inspired by the UAV reference image — fullscreen tactical map with floating overlay panels that can be minimized.

## Analysis

### Current Architecture

```
index.html
├── .app-container (flex-row)
│   ├── main.canvas-area (flex-grow, map)
│   └── aside.sidebar (380px fixed)
│       ├── header (SwarmControl title)
│       ├── nav.tab-bar (Training | Playground)
│       └── .panel-scroll
│           ├── Training Dashboard (accordion)
│           ├── ML Brain Status (accordion)
│           ├── Telemetry (accordion, shared)
│           ├── Performance (accordion)
│           ├── Viewport (accordion, shared)
│           ├── Inspector (accordion, shared)
│           ├── Legend (accordion, shared)
│           └── [8 Playground panels] (hidden when training mode)
```

**Key constraints:**
- Router is hash-based (`#training` / `#playground`), toggling panel visibility
- Canvas rendering (entities, terrain, fog) is shared — both modes render the same Rust WS stream
- State is a singleton module (`state.js`) — all panels read from it
- WebSocket connection is singleton — one WS pipe from Rust micro-core
- Training status is polled via HTTP (`/logs/run_latest/training_status.json`)
- Training stage data (goals, rules, graduation criteria) lives in `tactical_curriculum.json`

### What Needs to Change

The user wants to **split Training and Playground into separate pages** so they can run in parallel (two browser tabs). For the Training page specifically:

1. **Map takes fullscreen** — no sidebar, canvas fills the entire viewport
2. **Overlay dashboard** — floats on top of the map (glassmorphic, like the UAV reference)
3. **Minimize button** — collapses the dashboard to show only training-essential info
4. **Stage goal + ruleset** — dashboard must show current stage details from the curriculum

## Design Rationale

### Why Separate Pages (Not Just Tabs)

The current tab system is a **mode switch within a single page**. Both Training and Playground share:
- The same WebSocket connection
- The same canvas
- The same render loop

To truly run both simultaneously (watch training in one tab, experiment in playground in another), we need to decouple them into independent HTML entry points (or deep-route contexts), each with their own:
- WebSocket connection
- Canvas instance and render loop
- State module instance

**Recommendation:** Two separate Vite entry points (`training.html` and `playground.html`), each importing their respective panel modules. The shared modules (state, websocket, draw, config) remain as common imports.

### Overlay Dashboard Design (Training Page)

Inspired by the UAV Command Center reference:

```
┌─────────────────────────────────────────────────────────┐
│ FULLSCREEN MAP (canvas fills viewport)                  │
│                                                         │
│  ┌─ Top Bar (fixed) ──────────────────────────────────┐ │
│  │ [●] CONNECTED  │ SwarmControl │ Stage 1  │ [—][□] │ │
│  └────────────────────────────────────────────────────┘ │
│                                                         │
│                    [map content]                         │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  FLOATING OVERLAY DASHBOARD (bottom-left/right)  │   │
│  │                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  STAGE INFO  │  │  TELEMETRY   │              │   │
│  │  │  Goal: ...   │  │  TPS: 2400   │              │   │
│  │  │  Rules:      │  │  Tick: 45000 │              │   │
│  │  │  - Range 25  │  │  Entities:65 │              │   │
│  │  │  - DPS -25/s │  │              │              │   │
│  │  └──────────────┘  └──────────────┘              │   │
│  │                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  TRAINING    │  │  ML BRAIN    │              │   │
│  │  │  Ep: 659     │  │  Python: 🟢  │              │   │
│  │  │  WR: 50%     │  │  Dir: Hold   │              │   │
│  │  │  ■■■■□□□□□□  │  │              │              │   │
│  │  └──────────────┘  └──────────────┘              │   │
│  │                                                  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─ Bottom Hint ──────────────────────────────────────┐ │
│  │ Pan: drag · Zoom: scroll · Double-click: reset     │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Minimized State

When minimized, the dashboard collapses to a compact horizontal strip showing only:
- Stage badge + episode count
- Win rate bar (compact)
- Connection status
- Expand button

```
┌─────────────────────────────────────────────────────────┐
│ FULLSCREEN MAP                                          │
│                                                         │
│  ┌─ Minimized Dashboard ─────────────────────────────┐  │
│  │ [STAGE 1] EP 659 │ WR 50% ■■■□□ │ 🟢 │ [expand] │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│                    [map content]                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Stage Goal & Ruleset Display

**New data requirement:** The dashboard must display the current stage's:
1. **Stage name** — e.g., "Target Selection"
2. **Description/goal** — from `curriculum[stage].description`
3. **Combat rules** — from `combat.rules[]` (source → target, range, effects)
4. **Graduation criteria** — win rate threshold + min episodes
5. **Unlocked actions** — which actions are available at this stage

This data lives in `tactical_curriculum.json` and should be loaded at startup. The stage index comes from the training status poll.

## Recommendations

### Layout Architecture

1. **Create `training.html`** — new Vite entry point with fullscreen canvas + overlay DOM structure
2. **Create `src/training-main.js`** — imports only training-relevant modules (no playground panels)
3. **Keep `index.html` as playground** (for now), or rename to `playground.html` later
4. **Overlay panels use `position: fixed` / `absolute`** with glassmorphic styling (`backdrop-filter: blur()`, semi-transparent backgrounds)

### Overlay Dashboard Components

Split the overlay into distinct floating cards (like the UAV reference):

| Card | Position | Content |
|------|----------|---------|
| **Top Bar** | Top edge, full width | Connection badge, stage name, minimize/expand toggle |
| **Stage Info** | Top-right or bottom-left | Stage goal, description, graduation criteria, combat rules |
| **Training Metrics** | Bottom-left | Episode count (hero number), win rate bar, reward sparkline |
| **ML Brain** | Bottom-left (below metrics) | Python link, intervention, last directive |
| **Telemetry** | Bottom-right | TPS, tick, entity count, faction forces |
| **Perf Bars** | Bottom-right (below telemetry) | System performance meters |

### Glassmorphic Card Styling

```css
.overlay-card {
  background: rgba(8, 12, 18, 0.75);
  backdrop-filter: blur(12px) saturate(1.4);
  -webkit-backdrop-filter: blur(12px) saturate(1.4);
  border: 1px solid rgba(6, 214, 160, 0.12);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}
```

### Stage Ruleset Data Flow

```
1. training-main.js → fetch(`/profiles/tactical_curriculum.json`)
2. Parse → store as `window.__curriculum` or state export
3. Training status poll returns `{ stage: N }`
4. Stage card reads curriculum[N] → renders goal, rules, actions
5. Combat rules rendered as compact table
```

### Minimize Behavior

- Toggle via button in top bar
- Minimized = single compact strip at top or bottom
- Expanded = full overlay cards appear with slide-in animation
- State persisted to `localStorage` for user preference

## Two-Page Separation Strategy

### Shared Modules (no changes needed)
- `state.js` — each page gets its own module instance (ES module singleton per page)
- `websocket.js` — each page connects independently
- `config.js` — shared constants
- `draw/` — canvas rendering pipeline
- `components/sparkline.js` — reusable chart component

### Training Page Only
- `panels/training/dashboard.js` — redesigned as overlay card
- `panels/training/ml-brain.js` — redesigned as overlay card
- `panels/training/perf.js` — redesigned as overlay card
- `panels/shared/telemetry.js` — redesigned as overlay card
- **NEW:** `panels/training/stage-info.js` — stage goal + ruleset card
- **NEW:** `src/training-main.js` — entry point
- **NEW:** `training.html` — HTML template

### Playground Page Only (future)
- All `panels/playground/*.js` — kept as-is
- `panels/shared/*.js` — kept in sidebar
- Keep current `index.html` + `main.js`

### Vite Configuration

```js
// vite.config.js — multi-page build
export default {
  build: {
    rollupOptions: {
      input: {
        training: 'training.html',
        playground: 'index.html',  // or playground.html
      },
    },
  },
};
```

## Impact on Later Work

1. **Playground page** will be designed in a separate session (user's request)
2. **Shared modules** remain stable — no breaking changes to state, WebSocket, or draw pipeline
3. **Router module** will be simplified or removed — each page knows its own mode
4. **Current `main.js`** and `index.html` can serve as playground until explicitly redesigned

## Open Questions for User

1. **Dashboard position preference:** Should the expanded overlay cards be anchored to the **bottom edge** (like the UAV reference with UAV Center + Control Center at bottom), or should they be **top-right + bottom-left** (split positioning)?

2. **Stage info detail level:** Should the combat rules show the full table (all faction pairs, ranges, effects) or a compact summary? For early stages with 4 rules this is fine, but Stage 8-9 might have more complex rulesets.

3. **Auto-scroll to new stage:** When the training auto-graduates to a new stage, should the dashboard show a brief animation/toast announcing the stage change?

4. **Canvas hint:** Should the pan/zoom hint be kept or removed for cleaner aesthetics?
