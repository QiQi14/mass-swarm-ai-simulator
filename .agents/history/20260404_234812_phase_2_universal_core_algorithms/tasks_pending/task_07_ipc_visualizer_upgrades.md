---
Task_ID: task_07_ipc_visualizer_upgrades
Execution_Phase: Phase 2-3
Model_Tier: advanced
Target_Files:
  - micro-core/Cargo.toml
  - micro-core/src/plugins/mod.rs
  - micro-core/src/plugins/telemetry.rs
  - micro-core/src/lib.rs
  - micro-core/src/bridges/ws_protocol.rs
  - micro-core/src/systems/ws_sync.rs
  - micro-core/src/systems/ws_command.rs
  - debug-visualizer/index.html
  - debug-visualizer/style.css
  - debug-visualizer/visualizer.js
Dependencies:
  - task_03_flow_field_registry
  - task_04_rule_resources
Context_Bindings:
  - context/conventions
  - context/ipc-protocol
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Build the full **Telemetry & Debug Visualizer** — this is the primary debugging tool for all Phase 2 systems.

**Read `implementation_plan.md` AND the deep-dive spec `implementation_plan_task_07.md` (project root) for the complete architecture, code, and unit tests.**

> **CRITICAL:** This is an `advanced` tier task. The spec contains the Dual-Canvas architecture, PerfTelemetry pipeline, Sparkline class, Flow Field arrow rendering, Entity Inspector, Death Animations, Health Bars, Performance Bar Chart, and Faction Behavior Toggles. Read it ALL before starting.

**DO NOT modify `systems/mod.rs` — Task 08 handles wiring.**

## Architecture Mandates

### Zero-Cost Plugin Architecture
- **`TelemetryPlugin`** (Bevy Plugin) — owns `PerfTelemetry` resource + `flow_field_broadcast_system`
- **Cargo feature:** `debug-telemetry` (default = ON). Production: `--no-default-features` → zero overhead.
- **Systems use `Option<ResMut<PerfTelemetry>>`** — `None` in production, `Some` in dev.
- **WS protocol:** `SyncDelta.telemetry` is `Option<PerfTelemetry>` with `skip_serializing_if = "Option::is_none"`.
- **`FlowFieldSync` variant** — `#[cfg(feature = "debug-telemetry")]` → doesn't exist in production.

### Dual Canvas Layout
- `#canvas-bg` (z-index: 1) — Spatial Grid + Flow Field arrows. Redraws at ~2 TPS.
- `#canvas-entities` (z-index: 2) — 10K dots, health bars, death anims. Redraws at 60 FPS.
- CSS: both absolutely positioned, overlapping inside `.canvas-container`.

### Click-to-Inspect (NOT hover)
- `mousedown` on entity canvas → O(N) nearest entity search → lock ID
- Update inspector panel each frame from `entities.get(selectedId)`
- Auto-deselect if entity dies

## Rust Changes Summary

### 0. `Cargo.toml` [MODIFY]
Add `[features]` section: `default = ["debug-telemetry"]`, `debug-telemetry = []`

### 1. `plugins/telemetry.rs` [NEW] + `plugins/mod.rs` [NEW]
- Create `TelemetryPlugin` (Bevy Plugin) + `PerfTelemetry` resource struct
- Feature-gated: `#[cfg(feature = "debug-telemetry")]`
- Also houses `flow_field_broadcast_system`

### 1b. `lib.rs` [MODIFY]
Add `pub mod plugins;`

### 2. `bridges/ws_protocol.rs` [MODIFY]
- Add `removed: Vec<u32>` to `SyncDelta`
- Add `#[cfg(feature = "debug-telemetry")] telemetry: Option<PerfTelemetry>` to `SyncDelta` with `skip_serializing_if`
- Add `#[cfg(feature = "debug-telemetry")] FlowFieldSync` variant

### 3. `systems/ws_sync.rs` [MODIFY]
- Add `ResMut<RemovalEvents>`, `Option<ResMut<PerfTelemetry>>` to params
- Drain removal events, snapshot telemetry into SyncDelta (wrapped in Option)
- Always broadcast (even empty moved) so removal events always flow
- Add `flow_field_broadcast_system` in `plugins/telemetry.rs` (feature-gated)

### 4. `systems/ws_command.rs` [MODIFY]
- Add `set_faction_mode` command: `ResMut<FactionBehaviorMode>`, insert/remove from `static_factions`

## Visualizer Changes Summary

### 5. `index.html` [MODIFY]
- Dual canvas (`#canvas-bg` + `#canvas-entities`)
- Inspector panel (hidden by default, shows on click)
- System Performance panel with `#perf-bars` div
- Sparkline `<canvas>` elements next to each telemetry stat
- New layer toggles: Spatial Hash Grid, Flow Field Arrows
- Faction Behavior section with `#faction-toggles` div

### 6. `style.css` [MODIFY]
- Dual canvas overlay CSS
- Inspector grid layout
- Performance bar styles (green/yellow/red)
- Sparkline sizing
- Faction toggle button styles

### 7. `visualizer.js` [MODIFY — MAJOR UPGRADE]
- **Sparkline class:** Ring buffer of 60 samples, polyline on tiny canvas
- **Dual canvas rendering:** Background draws at ~2 TPS, entities at 60 FPS
- **Flow field cache:** `Map<factionId, {gridW, gridH, cellSize, vectors}>`
- **Background drawing:** Coordinate grid + spatial grid overlay + flow field arrows
- **Entity drawing:** Faction-batched dots + health bars + death animations
- **Entity Inspector:** Click handler, inspector panel update each frame
- **Performance bars:** Dynamic DOM creation, width + color from PerfTelemetry
- **Sparkline updates:** Push values each telemetry tick, redraw sparklines
- **Faction toggles:** Dynamic buttons from ADAPTER_CONFIG, send `set_faction_mode`
- **Handle `removed` array:** Death animation → delete from entities Map
- **Handle `FlowFieldSync` message:** Cache vectors, redraw background

## Unit Tests

### Rust:
- PerfTelemetry::default() — all zeros
- SyncDelta serde roundtrip — includes removed + telemetry
- FlowFieldSync serde roundtrip — includes vectors
- set_faction_mode command — toggles static_factions

### Manual Browser:
- Sparklines animate
- Perf bars show system timings
- Click entity → inspector shows data
- Toggle spatial grid → cell boundaries
- Toggle flow field → arrows render
- Faction toggle → behavior changes
- Entity death → fade ring animation
- Health bars appear when stat[0] < 1.0

---

# Verification_Strategy
Test_Type: unit + manual_steps
Test_Stack: cargo test (Rust), browser (JS)
Acceptance_Criteria:
  - "SyncDelta includes removed array and telemetry object"
  - "FlowFieldSync message broadcasts flow field vectors"
  - "PerfTelemetry resource populated by systems"
  - "Dual canvas: bg at ~2 TPS, entities at 60 FPS"
  - "Sparkline graphs track all telemetry values over time"
  - "Performance bar chart with green/yellow/red color coding"
  - "Click-to-inspect shows entity data in inspector panel"
  - "Spatial grid overlay toggleable"
  - "Flow field arrows toggleable"
  - "Health bars render only when damaged"
  - "Death animation on entity removal"
  - "Faction behavior toggles functional"
Suggested_Test_Commands:
  - "cd micro-core && cargo test ws_sync"
  - "cd micro-core && cargo test ws_command"
  - "cd micro-core && cargo test config"
Manual_Steps:
  - "Run micro-core, open debug-visualizer/index.html"
  - "Verify sparklines, perf bars, inspector, overlays, toggles"
