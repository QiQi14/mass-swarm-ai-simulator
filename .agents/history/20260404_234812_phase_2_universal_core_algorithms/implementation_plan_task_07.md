# Task 07 — Telemetry & Debug Visualizer (Full Specification)

> **Parent Plan:** [`implementation_plan.md`](./implementation_plan.md)
> **Architecture:** Dual-Canvas Rendering + PerfTelemetry Pipeline + Click Inspector
> **This file:** Exhaustive spec for the Executor agent.

**Phase:** 2–3 (Starts Phase 2, completes Phase 3) | **Tier:** `advanced` | **Domain:** IPC + Web UI + Instrumentation  
**Target Files:**
- `micro-core/Cargo.toml` [MODIFY] — `debug-telemetry` feature flag
- `micro-core/src/plugins/mod.rs` [NEW] — Plugin barrel file
- `micro-core/src/plugins/telemetry.rs` [NEW] — TelemetryPlugin + PerfTelemetry resource
- `micro-core/src/lib.rs` [MODIFY] — Add `pub mod plugins;`
- `micro-core/src/bridges/ws_protocol.rs` [MODIFY] — Protocol expansion
- `micro-core/src/systems/ws_sync.rs` [MODIFY] — Telemetry + removal broadcast
- `micro-core/src/systems/ws_command.rs` [MODIFY] — set_faction_mode
- `debug-visualizer/index.html` [MODIFY] — Dual canvas, inspector, perf panel, graphs
- `debug-visualizer/style.css` [MODIFY] — New panel styles
- `debug-visualizer/visualizer.js` [MODIFY] — Major upgrade

**Dependencies:** Task 03 (FlowFieldRegistry type), Task 04 (RemovalEvents, FactionBehaviorMode types)  
**Context Bindings:** `context/conventions`, `context/ipc-protocol`, `skills/rust-code-standards`

> **DO NOT** modify `systems/mod.rs` — Task 08 handles system wiring.

---

## 1. Design Principles

### Terminal vs Browser Separation

| Channel | Data Type | Why |
|---------|-----------|-----|
| **Terminal** (`RUST_LOG=debug`) | Text strings, state changes, errors | String formatting in Rust is cheap; `tracing` is zero-cost when disabled |
| **Browser** (WS) | **Numbers only** — `PerfTelemetry`, entity states, flow field vectors | Avoids V8 GC stutter from string parsing; numbers are natively fast in JSON |

> [!WARNING]
> **NEVER forward `info!()` text strings to the browser.** String serialization at 60 TPS will spike Rust CPU and cause JS GC pauses. Send only numeric payloads.

### Dual Canvas Architecture

```
┌─────────────────────────────────────────┐
│              <main>                      │
│  ┌───────────────────────────────────┐  │
│  │  #canvas-bg (z-index: 1)          │  │ ← Spatial Grid + Flow Field Arrows
│  │  Redraws at ~2 TPS               │  │   (only on FlowFieldSync message)
│  ├───────────────────────────────────┤  │
│  │  #canvas-entities (z-index: 2)    │  │ ← 10K dots + health bars + death anims
│  │  Redraws at 60 FPS               │  │   (every requestAnimationFrame)
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**Why:** Changing `fillStyle`/`beginPath()` is the #1 Canvas performance killer. Separating static overlays from dynamic entities means the background only redraws when flow field data arrives (~2 TPS), while entity rendering stays at 60 FPS.

---

## 2. Rust Changes

### 2.0 Cargo Feature Flag (`Cargo.toml` [MODIFY])

Add a feature flag so telemetry compiles out in production:

```toml
[features]
default = ["debug-telemetry"]
debug-telemetry = []
```

**Usage:**
- Development: `cargo run` (default features → telemetry ON)
- Production: `cargo build --release --no-default-features` (telemetry compiled out)

### 2.1 `micro-core/src/plugins/telemetry.rs` [NEW]

```rust
//! # Telemetry Plugin
//!
//! Debug-only plugin that provides system timing instrumentation.
//! Gated behind the `debug-telemetry` Cargo feature — compiles to zero
//! code in production builds.
//!
//! ## Ownership
//! - **Task:** task_07_ipc_visualizer_upgrades
//! - **Contract:** implementation_plan_task_07.md

use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Accumulated per-tick performance metrics.
/// Inserted as a Bevy Resource ONLY by TelemetryPlugin.
/// Systems access via `Option<ResMut<PerfTelemetry>>` — returns `None`
/// when the plugin is not loaded (production builds).
#[derive(Resource, Debug, Default, Clone, Serialize, Deserialize)]
pub struct PerfTelemetry {
    /// SpatialHashGrid rebuild time in microseconds
    pub spatial_us: u32,
    /// Flow field recalculation time in microseconds (0 when skipped)
    pub flow_field_us: u32,
    /// Interaction system time in microseconds
    pub interaction_us: u32,
    /// Removal system time in microseconds
    pub removal_us: u32,
    /// Movement system time in microseconds
    pub movement_us: u32,
    /// WS sync serialization time in microseconds
    pub ws_sync_us: u32,
    /// Total entity count this tick
    pub entity_count: u32,
}

/// Debug telemetry plugin. Inserts PerfTelemetry resource and
/// registers the flow_field_broadcast_system.
///
/// ## Zero-Cost in Production
/// When `debug-telemetry` feature is disabled:
/// - This plugin is not compiled
/// - PerfTelemetry resource doesn't exist
/// - `Option<ResMut<PerfTelemetry>>` in systems resolves to `None`
/// - `Instant::now()` is never called
/// - No telemetry data is serialized or broadcast
pub struct TelemetryPlugin;

impl Plugin for TelemetryPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<PerfTelemetry>();
        // flow_field_broadcast_system is registered here by Task 08
        // during integration wiring (it needs system ordering context)
    }
}
```

### 2.1b `micro-core/src/plugins/mod.rs` [NEW]

```rust
//! # Plugins
//!
//! Optional Bevy plugins, feature-gated for production builds.

#[cfg(feature = "debug-telemetry")]
pub mod telemetry;

#[cfg(feature = "debug-telemetry")]
pub use telemetry::{TelemetryPlugin, PerfTelemetry};
```

### 2.1c `micro-core/src/lib.rs` [MODIFY]

Add `pub mod plugins;` after existing module declarations.

### 2.2 System Timing Instrumentation Pattern

Systems use `Option<ResMut<PerfTelemetry>>` — when the resource is absent (production), the `Option` is `None` and zero work is done:

```rust
use crate::plugins::telemetry::PerfTelemetry;

pub fn some_system(
    telemetry: Option<ResMut<PerfTelemetry>>,
    // ... other params
) {
    // Only measure time if telemetry plugin is active
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    
    // ... system logic (UNCHANGED) ...
    
    // Write timing (no-op if telemetry is None)
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.some_field_us = s.elapsed().as_micros() as u32;
    }
}
```

> [!IMPORTANT]
> **The core system logic is NEVER modified.** The `Option` + `if let` pattern wraps AROUND the existing logic. When `debug-telemetry` is disabled, the `Option` is always `None`, and both `Instant::now()` and the timing write are skipped entirely.

For systems that run conditionally (flow_field_update_system skips most ticks):
```rust
if tick.tick % config.flow_field_update_interval != 0 {
    if let Some(mut t) = telemetry { t.flow_field_us = 0; }
    return;
}
```

### 2.3 `micro-core/src/bridges/ws_protocol.rs` [MODIFY]

Expand `WsMessage`. Note: `telemetry` is `Option<PerfTelemetry>` — omitted from JSON when telemetry plugin is not loaded:

```rust
#[cfg(feature = "debug-telemetry")]
use crate::plugins::telemetry::PerfTelemetry;

#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum WsMessage {
    /// Delta-sync: entity movement + removal + optional debug telemetry.
    SyncDelta {
        tick: u64,
        moved: Vec<EntityState>,
        #[serde(default)]
        removed: Vec<u32>,
        /// Present only when `debug-telemetry` feature is enabled.
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        telemetry: Option<PerfTelemetry>,
    },
    /// Flow field vector data for debug visualization.
    /// Only compiled when `debug-telemetry` feature is enabled.
    #[cfg(feature = "debug-telemetry")]
    FlowFieldSync {
        target_faction: u32,
        grid_width: u32,
        grid_height: u32,
        cell_size: f32,
        /// Flat array of [dx, dy] vectors, row-major order.
        vectors: Vec<[f32; 2]>,
    },
}
```

> [!WARNING]
> In production (`--no-default-features`), `SyncDelta` has NO `telemetry` field and `FlowFieldSync` variant doesn't exist. The JSON payload is minimal: `{type, tick, moved, removed}`.

### 2.4 `micro-core/src/systems/ws_sync.rs` [MODIFY]

```rust
#[cfg(feature = "debug-telemetry")]
use crate::plugins::telemetry::PerfTelemetry;

pub fn ws_sync_system(
    query: Query<(&EntityId, &Position, &Velocity, &FactionId, &StatBlock), Changed<Position>>,
    tick: Res<TickCounter>,
    sender: Res<BroadcastSender>,
    mut removal_events: ResMut<RemovalEvents>,
    // Option: telemetry is None in production builds
    telemetry: Option<ResMut<PerfTelemetry>>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());

    // Collect moved entities
    let mut moved = Vec::new();
    for (id, pos, vel, faction, stat_block) in query.iter() {
        moved.push(EntityState {
            id: id.id,
            x: pos.x, y: pos.y,
            dx: vel.dx, dy: vel.dy,
            faction_id: faction.0,
            stats: stat_block.0.to_vec(),
        });
    }

    // Drain removal events
    let removed = removal_events.removed_ids.clone();
    removal_events.removed_ids.clear();

    // Build message — telemetry field only present with feature
    let msg = WsMessage::SyncDelta {
        tick: tick.tick,
        moved,
        removed,
        #[cfg(feature = "debug-telemetry")]
        telemetry: telemetry.as_ref().map(|t| {
            let mut snapshot = (*t).clone();
            snapshot.entity_count = query.iter().count() as u32;
            snapshot
        }),
    };

    if let Ok(json_str) = serde_json::to_string(&msg) {
        let _ = sender.0.send(json_str);
    }

    // Write own timing
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.ws_sync_us = s.elapsed().as_micros() as u32;
    }
}
```

### 2.5 Flow Field Sync (broadcast at ~2 TPS) — Feature-Gated

This entire system is compiled ONLY with `debug-telemetry`. Add to `plugins/telemetry.rs`:

```rust
/// Broadcasts flow field vectors to the debug visualizer.
/// Compiled only with `debug-telemetry` feature.
pub fn flow_field_broadcast_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    registry: Res<FlowFieldRegistry>,
    sender: Res<BroadcastSender>,
) {
    if tick.tick == 0 || tick.tick % config.flow_field_update_interval != 0 {
        return;
    }

    for (&faction_id, field) in registry.fields.iter() {
        let grid_w = field.width();
        let grid_h = field.height();

        let mut vectors = Vec::with_capacity(grid_w * grid_h);
        for y in 0..grid_h {
            for x in 0..grid_w {
                let dir = field.get_direction(x, y);
                vectors.push([dir.x, dir.y]);
            }
        }

        let msg = WsMessage::FlowFieldSync {
            target_faction: faction_id,
            grid_width: grid_w as u32,
            grid_height: grid_h as u32,
            cell_size: field.cell_size(),
            vectors,
        };

        if let Ok(json_str) = serde_json::to_string(&msg) {
            let _ = sender.0.send(json_str);
        }
    }
}
```

> [!IMPORTANT]
> The executor must verify that `FlowField` exposes `width()`, `height()`, `cell_size()`, and `get_direction(x, y) -> Vec2` methods. If the Task 03 implementation uses different API names, adapt accordingly. DO NOT assume the spec code compiles verbatim.

### 2.6 `micro-core/src/systems/ws_command.rs` [MODIFY]

Add `set_faction_mode` command:

```rust
// Add to ws_command_system params:
mut behavior_mode: ResMut<FactionBehaviorMode>,

// Inside the command match:
"set_faction_mode" => {
    if let (Some(faction_id), Some(mode)) = (
        params.get("faction_id").and_then(|v| v.as_u64()).map(|v| v as u32),
        params.get("mode").and_then(|v| v.as_str()),
    ) {
        match mode {
            "static" => { behavior_mode.static_factions.insert(faction_id); }
            "brain"  => { behavior_mode.static_factions.remove(&faction_id); }
            _ => { warn!("Unknown mode: {}", mode); }
        }
        info!("Faction {} mode set to: {}", faction_id, mode);
    }
}
```

### 2.7 Plugin Architecture & Instrumentation Standard

**The Plugin Lifecycle:**
```
┌─────────────────────────────────────────────────────────────┐
│ cargo run                    (default features)             │
│  └─ debug-telemetry = ON                                    │
│     └─ TelemetryPlugin inserted                             │
│        └─ PerfTelemetry resource exists                     │
│           └─ Option<ResMut<PerfTelemetry>> = Some(...)       │
│              └─ Instant::now() called, timing written        │
│                 └─ SyncDelta.telemetry = Some({...})         │
│                    └─ Browser shows perf bars + sparklines   │
├─────────────────────────────────────────────────────────────┤
│ cargo build --release --no-default-features                 │
│  └─ debug-telemetry = OFF                                   │
│     └─ TelemetryPlugin NOT compiled                         │
│        └─ PerfTelemetry resource does NOT exist             │
│           └─ Option<ResMut<PerfTelemetry>> = None            │
│              └─ Instant::now() NEVER called                  │
│                 └─ SyncDelta has NO telemetry field          │
│                    └─ Zero overhead                          │
└─────────────────────────────────────────────────────────────┘
```

**Required additions per task:**
- **Task 07 (this task):** Creates `TelemetryPlugin`, `PerfTelemetry` in `plugins/telemetry.rs`. Adds `Option<ResMut<PerfTelemetry>>` timing to `ws_sync_system` (own file). Creates `flow_field_broadcast_system` in `plugins/telemetry.rs`.
- **Task 08 (Integration):** 
  - Adds `#[cfg(feature = "debug-telemetry")] app.add_plugins(TelemetryPlugin)` in `main.rs`
  - Adds `Option<ResMut<PerfTelemetry>>` + timing wrapper to ALL other systems:
    - `update_spatial_grid_system` → `telemetry.spatial_us`
    - `interaction_system` → `telemetry.interaction_us`
    - `removal_system` → `telemetry.removal_us`
    - `movement_system` → `telemetry.movement_us`
    - `flow_field_update_system` → `telemetry.flow_field_us`
  - Registers `flow_field_broadcast_system` in the system DAG (after ws_sync)

> [!WARNING]
> **DO NOT** patch Tasks 02, 05, or 06 to add telemetry. Those tasks run before Task 07 creates the plugin. Task 08 handles all cross-cutting instrumentation using the `Option<ResMut>` pattern.

---

## 3. Visualizer Changes

### 3.1 HTML Structure Changes (`index.html`)

Replace single canvas with dual canvas:
```html
<main class="canvas-container">
    <canvas id="canvas-bg"></canvas>
    <canvas id="canvas-entities"></canvas>
    <!-- Connection status + hint overlays stay -->
</main>
```

Add Inspector Panel (new section in sidebar):
```html
<section id="inspector-panel" class="panel-section" style="display: none;">
    <h2>Entity Inspector</h2>
    <div class="inspector-grid">
        <span class="inspector-label">ID</span>
        <span id="insp-id" class="inspector-value mono">—</span>
        <span class="inspector-label">Faction</span>
        <span id="insp-faction" class="inspector-value mono">—</span>
        <span class="inspector-label">Position</span>
        <span id="insp-pos" class="inspector-value mono">—</span>
        <span class="inspector-label">Velocity</span>
        <span id="insp-vel" class="inspector-value mono">—</span>
        <span class="inspector-label">Stats</span>
        <span id="insp-stats" class="inspector-value mono">—</span>
    </div>
    <button id="insp-deselect" class="btn secondary">Deselect</button>
</section>
```

Add System Performance Panel:
```html
<section class="panel-section">
    <h2>System Performance</h2>
    <div id="perf-bars" class="perf-bar-chart">
        <!-- Populated dynamically from PerfTelemetry -->
    </div>
</section>
```

Add Sparkline canvases next to each telemetry stat:
```html
<div class="stat-box">
    <span class="stat-label">TPS</span>
    <div class="stat-with-graph">
        <span id="stat-tps" class="stat-value mono">0</span>
        <canvas id="graph-tps" class="sparkline" width="80" height="24"></canvas>
    </div>
</div>
```

Add new layer toggles:
```html
<label class="toggle-control">
    <input type="checkbox" id="toggle-spatial-grid">
    <span class="control-indicator"></span>
    <span class="control-label">Spatial Hash Grid</span>
</label>
<label class="toggle-control">
    <input type="checkbox" id="toggle-flow-field">
    <span class="control-indicator"></span>
    <span class="control-label">Flow Field Arrows</span>
</label>
```

Add Faction Behavior Toggles (dynamically generated in JS):
```html
<section class="panel-section">
    <h2>Faction Behavior</h2>
    <div id="faction-toggles"></div>
</section>
```

### 3.2 CSS Additions (`style.css`)

```css
/* Dual canvas overlay */
.canvas-container { position: relative; }
.canvas-container canvas {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
}
#canvas-bg { z-index: 1; }
#canvas-entities { z-index: 2; }

/* Inspector panel */
.inspector-grid {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 4px 12px;
}
.inspector-label { color: var(--text-secondary); font-size: 0.75rem; }
.inspector-value { font-size: 0.85rem; }

/* Performance bar chart */
.perf-bar-chart { display: flex; flex-direction: column; gap: 4px; }
.perf-bar-row {
    display: flex; align-items: center; gap: 8px;
}
.perf-bar-label { width: 80px; font-size: 0.7rem; color: var(--text-secondary); }
.perf-bar-track { flex: 1; height: 12px; background: var(--surface); border-radius: 6px; overflow: hidden; }
.perf-bar-fill { height: 100%; border-radius: 6px; transition: width 0.15s ease; }
.perf-bar-fill.green { background: #30d158; }
.perf-bar-fill.yellow { background: #ffd60a; }
.perf-bar-fill.red { background: #ff453a; }
.perf-bar-value { width: 50px; text-align: right; font-size: 0.7rem; font-family: var(--font-mono); }

/* Sparkline */
.stat-with-graph { display: flex; align-items: center; gap: 6px; }
.sparkline { width: 80px; height: 24px; opacity: 0.8; }

/* Faction toggle buttons */
.faction-toggle-btn {
    display: flex; justify-content: space-between; align-items: center;
    width: 100%; padding: 8px 12px; margin-bottom: 4px;
    border: 1px solid var(--border); border-radius: 6px;
    background: var(--surface); color: var(--text-primary);
    cursor: pointer; font-size: 0.8rem;
}
.faction-toggle-btn:hover { background: var(--surface-hover); }
.faction-mode-badge {
    padding: 2px 8px; border-radius: 3px; font-size: 0.65rem;
    text-transform: uppercase; font-weight: 700;
}
.faction-mode-badge.static { background: rgba(255,69,58,0.2); color: #ff453a; }
.faction-mode-badge.brain { background: rgba(48,209,88,0.2); color: #30d158; }
```

### 3.3 JavaScript Architecture (`visualizer.js`)

#### 3.3a Sparkline Class

```javascript
class Sparkline {
    constructor(canvasId, maxSamples = 60, color = '#30d158') {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.samples = [];
        this.maxSamples = maxSamples;
        this.color = color;
    }

    push(value) {
        this.samples.push(value);
        if (this.samples.length > this.maxSamples) this.samples.shift();
    }

    draw() {
        const { canvas, ctx, samples, color } = this;
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        if (samples.length < 2) return;

        const max = Math.max(...samples, 1);
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < samples.length; i++) {
            const x = (i / (this.maxSamples - 1)) * w;
            const y = h - (samples[i] / max) * (h - 2);
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        }
        ctx.stroke();
    }
}
```

#### 3.3b Flow Field Cache & Background Drawing

```javascript
// Cached flow field data (per faction)
const flowFieldCache = new Map(); // Map<factionId, { gridW, gridH, cellSize, vectors }>

// On FlowFieldSync message:
function handleFlowFieldSync(msg) {
    flowFieldCache.set(msg.target_faction, {
        gridW: msg.grid_width,
        gridH: msg.grid_height,
        cellSize: msg.cell_size,
        vectors: msg.vectors,
    });
    drawBackground(); // Redraw background canvas (~2 TPS)
}

function drawBackground() {
    const bgCtx = bgCanvas.getContext('2d');
    bgCtx.clearRect(0, 0, bgCanvas.width, bgCanvas.height);
    bgCtx.fillStyle = COLOR_BG;
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);

    if (showGrid) drawCoordinateGrid(bgCtx);
    if (showSpatialGrid) drawSpatialGrid(bgCtx);
    if (showFlowField) drawFlowFieldArrows(bgCtx);
}
```

#### 3.3c Entity Inspector (Click-to-Select)

```javascript
let selectedEntityId = null;

canvasEntities.addEventListener('mousedown', (e) => {
    if (hasDragged) return;
    const rect = canvasEntities.getBoundingClientRect();
    const [wx, wy] = canvasToWorld(e.clientX - rect.left, e.clientY - rect.top);

    // O(N) nearest-entity search (single click, not per-frame)
    let bestDist = Infinity;
    let bestId = null;
    for (const [id, ent] of entities) {
        const dx = ent.x - wx, dy = ent.y - wy;
        const dist = dx * dx + dy * dy;
        if (dist < bestDist) {
            bestDist = dist;
            bestId = id;
        }
    }

    // Selection threshold (world units)
    if (bestId !== null && bestDist < 100) { // 10 world units squared
        selectedEntityId = bestId;
        updateInspectorPanel();
        document.getElementById('inspector-panel').style.display = 'block';
    }
});

function updateInspectorPanel() {
    if (selectedEntityId === null) return;
    const ent = entities.get(selectedEntityId);
    if (!ent) { deselectEntity(); return; }

    const factionName = ADAPTER_CONFIG.factions[ent.faction_id]?.name || `Faction ${ent.faction_id}`;
    document.getElementById('insp-id').textContent = selectedEntityId;
    document.getElementById('insp-faction').textContent = factionName;
    document.getElementById('insp-pos').textContent = `(${ent.x.toFixed(1)}, ${ent.y.toFixed(1)})`;
    document.getElementById('insp-vel').textContent = `(${ent.dx.toFixed(2)}, ${ent.dy.toFixed(2)})`;
    document.getElementById('insp-stats').textContent = (ent.stats || []).map(s => s.toFixed(2)).join(', ');
}
```

#### 3.3d Performance Bar Chart

```javascript
const PERF_SYSTEMS = [
    { key: 'spatial_us', label: 'Spatial Grid' },
    { key: 'flow_field_us', label: 'Flow Field' },
    { key: 'interaction_us', label: 'Interaction' },
    { key: 'removal_us', label: 'Removal' },
    { key: 'movement_us', label: 'Movement' },
    { key: 'ws_sync_us', label: 'WS Sync' },
];

function updatePerfBars(telemetry) {
    const container = document.getElementById('perf-bars');
    // Build bars dynamically on first call, update fill widths thereafter
    for (const sys of PERF_SYSTEMS) {
        const us = telemetry[sys.key] || 0;
        let row = document.getElementById(`perf-${sys.key}`);
        if (!row) {
            // Create DOM on first call
            row = document.createElement('div');
            row.id = `perf-${sys.key}`;
            row.className = 'perf-bar-row';
            row.innerHTML = `
                <span class="perf-bar-label">${sys.label}</span>
                <div class="perf-bar-track"><div class="perf-bar-fill"></div></div>
                <span class="perf-bar-value mono">0µs</span>`;
            container.appendChild(row);
        }
        const fill = row.querySelector('.perf-bar-fill');
        const valueEl = row.querySelector('.perf-bar-value');
        const pct = Math.min(100, (us / 2000) * 100); // 2000µs = 100%
        fill.style.width = pct + '%';
        fill.className = 'perf-bar-fill ' + (us < 200 ? 'green' : us < 1000 ? 'yellow' : 'red');
        valueEl.textContent = us + 'µs';
    }
}
```

#### 3.3e Health Bars

Draw health bars ONLY when `stat[0] < 1.0`:

```javascript
function drawHealthBars(ctx) {
    const barW = 10, barH = 2;
    for (const ent of entities.values()) {
        if (!ent.stats || ent.stats[0] === undefined || ent.stats[0] >= 1.0) continue;

        const [cx, cy] = worldToCanvas(ent.x, ent.y);
        if (cx < cullLeft || cx > cullRight || cy < cullTop || cy > cullBottom) continue;

        const scale = getScaleFactor();
        const bw = barW * scale, bh = barH * scale;
        const hp = Math.max(0, ent.stats[0]); // 0.0–1.0

        // Background
        ctx.fillStyle = 'rgba(255,255,255,0.15)';
        ctx.fillRect(cx - bw/2, cy - 8*scale, bw, bh);

        // Fill (green→red lerp)
        const r = Math.round(255 * (1 - hp));
        const g = Math.round(255 * hp);
        ctx.fillStyle = `rgb(${r}, ${g}, 50)`;
        ctx.fillRect(cx - bw/2, cy - 8*scale, bw * hp, bh);
    }
}
```

#### 3.3f Death Animations

```javascript
const deathAnimations = [];

function addDeathAnimation(id) {
    const ent = entities.get(id);
    if (ent) {
        deathAnimations.push({
            x: ent.x, y: ent.y,
            startTime: performance.now(),
            factionId: ent.faction_id,
        });
    }
    entities.delete(id);
}

function drawDeathAnimations(ctx) {
    const now = performance.now();
    for (let i = deathAnimations.length - 1; i >= 0; i--) {
        const anim = deathAnimations[i];
        const elapsed = now - anim.startTime;
        if (elapsed > 500) { deathAnimations.splice(i, 1); continue; }

        const progress = elapsed / 500;
        const scale = getScaleFactor();
        const radius = (ENTITY_RADIUS + progress * ENTITY_RADIUS * 3) * scale;
        const alpha = 1.0 - progress;

        const [cx, cy] = worldToCanvas(anim.x, anim.y);
        const color = ADAPTER_CONFIG.factions[anim.factionId]?.color || '#fff';
        ctx.strokeStyle = color.replace(')', `, ${alpha})`).replace('rgb', 'rgba');
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        ctx.stroke();
    }
}
```

#### 3.3g Faction Behavior Toggles

```javascript
function initFactionToggles() {
    const container = document.getElementById('faction-toggles');
    const defaultStatic = new Set([1]); // FactionBehaviorMode::default()

    for (const [factionIdStr, config] of Object.entries(ADAPTER_CONFIG.factions)) {
        const factionId = parseInt(factionIdStr);
        let isStatic = defaultStatic.has(factionId);

        const btn = document.createElement('button');
        btn.className = 'faction-toggle-btn';
        btn.innerHTML = `
            <span>${config.name}</span>
            <span class="faction-mode-badge ${isStatic ? 'static' : 'brain'}">${isStatic ? 'Static' : 'Brain'}</span>
        `;
        btn.style.borderLeftColor = config.color;
        btn.style.borderLeftWidth = '3px';

        btn.addEventListener('click', () => {
            isStatic = !isStatic;
            const badge = btn.querySelector('.faction-mode-badge');
            badge.textContent = isStatic ? 'Static' : 'Brain';
            badge.className = `faction-mode-badge ${isStatic ? 'static' : 'brain'}`;
            sendCommand('set_faction_mode', { faction_id: factionId, mode: isStatic ? 'static' : 'brain' });
        });

        container.appendChild(btn);
    }
}
```

---

## 4. Corrections from Human-Provided Code

| # | User's Code | Issue | Correction |
|---|-------------|-------|------------|
| 1 | `entities.filter(e => e.faction_id === 0)` | Creates new array = GC pressure | Current code already batches correctly — iterate Map once per faction |
| 2 | `ctx.arc(e.x, e.y, ...)` using raw world coords | Missing `worldToCanvas()` transform | Must apply view transform for pan/zoom |
| 3 | `PerfTelemetry` fields as `u64` | `as_micros()` → `u128`, system times always < 4B µs | Use `u32` — smaller JSON, sufficient range |
| 4 | `flow_field_broadcast_system` assumes `field.width()` API | Task 03 FlowField API not finalized | Executor must verify actual method names from Task 03 implementation |

---

## 5. Edge Cases

| Edge Case | Handling |
|-----------|----------|
| No entities moved this tick | Still broadcast SyncDelta with empty `moved` — telemetry stays live |
| Selected entity dies | Inspector detects missing ID → auto-deselect |
| Flow field not yet calculated | `flowFieldCache` empty → skip arrow drawing |
| Sparkline has < 2 samples | Skip drawing (handled in `draw()`) |
| 10K entities health bars | Only draw when `stat[0] < 1.0` — typically ~10% of entities |
| Zero division in perf bar | `Math.min(100, ...)` prevents overflow |

---

## 6. Unit Tests

### Rust Tests:
- `PerfTelemetry::default()` — all fields 0
- `WsMessage::SyncDelta` serde — includes `removed` and `telemetry` fields
- `WsMessage::FlowFieldSync` serde — includes `vectors` as `Vec<[f32; 2]>`
- `set_faction_mode` command — toggle faction 1 to "brain", verify removed from static set
- `ws_sync_system` — broadcasts telemetry with entity data

### Manual Browser Tests:
- Connect to running simulation → telemetry numbers update live
- Sparkline graphs show rolling history
- Performance bars color-code (green/yellow/red) based on timing
- Click entity → inspector shows correct data
- Toggle "Spatial Hash Grid" → cell boundaries visible
- Toggle "Flow Field Arrows" → directional lines render
- Click faction toggle → behavior changes, button updates
- Entity dies → expanding fade ring animation
- Health bars appear only when stat[0] < 1.0

---

## 7. Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit + manual_steps
  Test_Stack: cargo test + browser
  Acceptance_Criteria:
    - "SyncDelta contains removed array and telemetry object"
    - "FlowFieldSync message contains vectors array"
    - "PerfTelemetry resource populated by systems"
    - "Dual canvas: background redraws at ~2 TPS, entities at 60 FPS"
    - "Sparkline graphs track telemetry values over time"
    - "Performance bar chart shows system timing with color coding"
    - "Click-to-inspect entity shows ID, faction, position, velocity, stats"
    - "Spatial grid overlay toggleable"
    - "Flow field arrows toggleable"
    - "Health bars render only when damaged"
    - "Death animation plays on entity removal"
    - "Faction behavior toggles send WS commands"
    - "set_faction_mode command modifies FactionBehaviorMode"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test ws_sync"
    - "cd micro-core && cargo test ws_command"
    - "cd micro-core && cargo test config"
  Manual_Steps:
    - "Run micro-core, open debug-visualizer/index.html"
    - "Verify sparkline graphs animate next to telemetry values"
    - "Verify perf bars show system timings"
    - "Click entity → inspector panel shows data"
    - "Toggle spatial grid → cell boundaries visible"
    - "Toggle flow field → arrows render"
    - "Click faction toggle → behavior changes"
    - "Watch entity die → fade ring animation"
```
