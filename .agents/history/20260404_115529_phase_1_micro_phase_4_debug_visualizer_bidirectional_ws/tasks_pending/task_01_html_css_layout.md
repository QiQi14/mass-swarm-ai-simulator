# Task 01: Debug Visualizer — HTML + CSS Layout & Styling

Task_ID: task_01_html_css_layout
Execution_Phase: A
Model_Tier: advanced

## Target_Files
- `debug-visualizer/index.html` [NEW]
- `debug-visualizer/style.css` [NEW]

## Dependencies
- None

## Context_Bindings
- context/conventions
- context/architecture

## Strict_Instructions

Create the Debug Visualizer page — a real-time simulation dashboard for monitoring and controlling a headless mass-swarm AI simulation. You have **full creative freedom** over the visual design, layout, and aesthetics. The only hard constraints are the **functional requirements** and **DOM ID contract** below.

### Design Context

This is a **developer debugging tool** for a mass-swarm simulation (10,000+ entities). Think mission-control, real-time monitoring dashboards, or game engine debug panels. It will be used for long sessions, so dark mode and readability are important. The design should feel professional and information-dense but not cluttered.

**Tech constraint:** Vanilla HTML + CSS only. No frameworks, no build tools, no npm. The page links to `visualizer.js` (created separately) which handles all interactivity.

### Functional Requirements

#### F1: Main Canvas Viewport
- A large `<canvas>` element that serves as the primary visualization area
- Must fill the majority of the viewport (it's the hero element)
- Will render a grid-based map with entity dots (handled by JS)

#### F2: Telemetry Panel
A panel displaying real-time system health metrics:
- **TPS** (Ticks Per Second) — actual simulation tick rate
- **WS Ping** — WebSocket round-trip latency
- **AI Latency** — Python AI response time (may show "N/A" initially)
- **Entity Count** — total entities alive
- **Swarm / Defender breakdown** — count per team
- **Current Tick** — simulation tick number

#### F3: Control Panel
Controls for interacting with the simulation:
- **Play/Pause toggle** — single button that toggles simulation state
- **Step button** — advance simulation by N ticks (for collision debugging)
- **Step count input** — number input for how many ticks to step (default: 1)

#### F4: Layer Toggles
Visual layer controls (checkboxes or toggle switches):
- **Grid** — show/hide coordinate grid overlay (default: ON)
- **Velocity Vectors** — show/hide movement direction lines on entities (default: OFF)
- **Fog of War** — show/hide fog overlay (default: OFF, placeholder for future)

#### F5: Connection Status
- Visual indicator of WebSocket connection state (connected / disconnected / reconnecting)
- Must be immediately visible without scrolling

#### F6: Legend
- Color key for entity teams (swarm vs defender)

#### F7: Spawn on Click (Canvas interaction)
- The canvas itself is the spawn target — clicking on it spawns entities at that position
- No special HTML needed for this (JS handles it), but the canvas must be interactive

### DOM ID Contract (MANDATORY)

These IDs are referenced by `visualizer.js`. They MUST exist in the HTML exactly as listed:

```
Canvas:          sim-canvas
Telemetry:       stat-tps, stat-ping, stat-ai-latency, stat-entities, stat-swarm, stat-defender, stat-tick
Controls:        play-pause-btn, step-btn, step-count-input
Layer toggles:   toggle-grid, toggle-velocity, toggle-fog
Connection:      status-dot, status-text
```

You MAY add additional IDs, classes, wrapper elements, or decorative elements as needed for your design. The above are the minimum required set.

### CSS Requirements (Minimal Constraints)

- **Dark theme** — the only hard requirement on colors
- **Responsive** — should degrade gracefully on smaller viewports
- **No inline styles** — all styling in `style.css`
- **Interactive elements must have visual feedback** (hover/focus/active states)
- Everything else (color palette, typography, spacing, animations, layout direction, panel placement) is YOUR creative decision

### What NOT to Include
- No JavaScript logic — only `<script src="visualizer.js"></script>` at end of body
- No external dependencies except optionally a web font (Google Fonts via CDN is OK)

## Verification_Strategy
  Test_Type: manual_steps
  Acceptance_Criteria:
    - "Opening index.html shows a dark-themed dashboard with canvas, telemetry, controls, layer toggles, and legend"
    - "All mandatory DOM IDs from the contract exist"
    - "Canvas occupies the majority of the viewport"
    - "Play/Pause button, Step button, step count input are present and styled"
    - "Layer toggles (grid, velocity, fog) are present"
    - "Connection status indicator is visible"
    - "Responsive: layout adapts at narrow viewports without breaking"
    - "Page looks professional and polished"
  Manual_Steps:
    - "Open debug-visualizer/index.html in Chrome"
    - "Use DevTools to verify all mandatory IDs exist"
    - "Verify dark theme and visual polish"
    - "Verify interactive elements have hover/focus states"
    - "Resize window to verify responsive behavior"
