# Feature 5: Debug Visualizer — Phase 3 Observability Tools

> **Tasks:** 11 (Rust WS Protocol Upgrade), 12 (Frontend UI)
> **Domain:** Rust (WS bridge) + HTML/CSS/JS (debug-visualizer/)
> **Phase:** Phase 1 (parallel with T01-T04) — enabled by extracting resource defs to T02

---

## Motivation

Phase 3 introduces 8 new MacroDirectives, sub-factions, zone modifiers, aggro masks, and EngineOverride. Without visualizer support for these, development is blind:

| Feature | If NOT Visualized | Risk |
|---------|-------------------|------|
| Zone Modifiers | Can't see attraction/repulsion zones | Can't debug why entities cluster or avoid an area |
| SplitFaction | Can't see which entities were re-tagged | Can't verify epicenter selection or percentage |
| AggroMask | Can't see which faction pairs are combat-suppressed | Can't verify "The Blinders" flanking maneuver |
| EngineOverride | Can't see which entities are under Tier 1 control | Can't debug intervention interference |
| Density Heatmaps | Can't see what the ML Brain "sees" | Can't correlate ML decisions with entity positions |
| ML Status | Can't see if Python is connected or what it last sent | Total blind spot during training |
| Sub-Faction Colors | All entities look the same after split | Can't visually confirm split happened |

---

## Task 11: WS Protocol & Command Upgrade (Rust)

**Task_ID:** `task_11_ws_protocol_phase3`
**Execution_Phase:** 1 (parallel — runs alongside T01, T03, T04)
**Model_Tier:** `standard`
**Target_Files:**
  - `micro-core/src/bridges/ws_protocol.rs` (MODIFY)
  - `micro-core/src/systems/ws_sync.rs` (MODIFY)
  - `micro-core/src/systems/ws_command.rs` (MODIFY)
**Dependencies:** Task 02 (Phase 3 resource types: `ActiveZoneModifiers`, `AggroMaskRegistry`, `LatestDirective`, etc.)
**Context_Bindings:**
  - `context/ipc-protocol`
  - `context/conventions`
  - `skills/rust-code-standards`

> [!NOTE]
> **Why Phase 1?** T11 only needs the resource *types* (data-only structs from T02), not the
> system *logic* (T05). Since T02 defines all resource types in Phase 1, T11 can read/write
> them via `Res<T>`/`ResMut<T>` immediately. The data will be empty until T05 populates it,
> but the WS commands and broadcast fields are fully functional.

### Part A: Extend WS Broadcast (`ws_sync.rs` + `ws_protocol.rs`)

The `SyncDelta` message must include new Phase 3 state for the visualizer to render. All new fields are behind `#[cfg(feature = "debug-telemetry")]` and `#[serde(skip_serializing_if = "Option::is_none")]` to avoid bloating non-debug builds.

#### New WS Protocol Types

```rust
// ws_protocol.rs additions

/// Active zone modifier state for debug overlay rendering.
#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZoneModifierSync {
    pub target_faction: u32,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub cost_modifier: f32,
    pub ticks_remaining: u32,
}

/// ML Brain status for debug panel.
#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MlBrainSync {
    /// Last directive received from Python (serialized as JSON string)
    pub last_directive: Option<String>,
    /// Whether the ZMQ bridge has an active Python connection
    pub python_connected: bool,
    /// Whether any EngineOverride is active (Tier 1 intervention)
    pub intervention_active: bool,
}

/// Aggro mask state for debug rendering.
#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggroMaskSync {
    pub source_faction: u32,
    pub target_faction: u32,
    pub allow_combat: bool,
}
```

#### Extended SyncDelta

```rust
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum WsMessage {
    SyncDelta {
        tick: u64,
        moved: Vec<EntityState>,
        #[serde(default)]
        removed: Vec<u32>,

        // ── Existing debug fields ──
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        telemetry: Option<PerfTelemetry>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        visibility: Option<VisibilitySync>,

        // ── NEW Phase 3 debug fields ──

        /// Active zone modifiers (pheromone gravity wells).
        /// Updated every tick for smooth radius animation.
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        zone_modifiers: Option<Vec<ZoneModifierSync>>,

        /// Active sub-factions (created by SplitFaction).
        /// UI uses this to assign distinct colors.
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        active_sub_factions: Option<Vec<u32>>,

        /// Aggro mask state (SetAggroMask).
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        aggro_masks: Option<Vec<AggroMaskSync>>,

        /// ML Brain status.
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        ml_brain: Option<MlBrainSync>,

        /// Density heatmap for the active fog faction (or brain faction 0).
        /// Flat Vec<f32> of size grid_w × grid_h, normalized [0, 1].
        /// Sent every 6 ticks (~10 TPS) to avoid bandwidth explosion.
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        density_heatmap: Option<Vec<f32>>,
    },
    // ... existing FlowFieldSync ...
}
```

#### Populate in `ws_sync_system`

```rust
// Every 6 ticks (aligned with visibility sync):
let zone_modifiers = if tick.tick % 6 == 0 {
    Some(zones.zones.iter().map(|z| ZoneModifierSync {
        target_faction: z.target_faction,
        x: z.x, y: z.y,
        radius: z.radius,
        cost_modifier: z.cost_modifier,
        ticks_remaining: z.ticks_remaining,
    }).collect())
} else { None };

let active_sub_factions = if tick.tick % 6 == 0 {
    Some(sub_factions.factions.clone())
} else { None };

let aggro_masks_sync = if tick.tick % 6 == 0 {
    Some(aggro.masks.iter().map(|((s, t), &v)| AggroMaskSync {
        source_faction: *s, target_faction: *t, allow_combat: v,
    }).collect())
} else { None };

let ml_brain = Some(MlBrainSync {
    last_directive: latest_directive.directive.as_ref().map(|d| {
        serde_json::to_string(d).unwrap_or_default()
    }),
    python_connected: /* check ZMQ connection state */,
    intervention_active: intervention.active,
});

// Density heatmap for the visualizer's active faction
let density_heatmap = if tick.tick % 6 == 0 {
    // Use the vectorizer to build density for the active fog faction
    // (if no fog faction selected, default to faction 0)
    let target = fog_faction.0.unwrap_or(0);
    density_maps.get(&target).cloned()
} else { None };
```

### Part B: New WS Commands (`ws_command.rs`)

Add 7 new commands for interactive AI debugging from the browser:

#### 1. `place_zone_modifier` — Interactive pheromone placement

```rust
"place_zone_modifier" => {
    let target_faction = cmd.params.get("target_faction").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let x = cmd.params.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
    let y = cmd.params.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
    let radius = cmd.params.get("radius").and_then(|v| v.as_f64()).unwrap_or(100.0) as f32;
    let cost_modifier = cmd.params.get("cost_modifier").and_then(|v| v.as_f64()).unwrap_or(-50.0) as f32;
    let duration = cmd.params.get("duration_ticks").and_then(|v| v.as_u64()).unwrap_or(300) as u32;

    zones.zones.push(ZoneModifier {
        target_faction, x, y, radius, cost_modifier, ticks_remaining: duration,
    });
    println!("[WS Command] place_zone_modifier faction={} at ({}, {}) r={} cost={}", target_faction, x, y, radius, cost_modifier);
}
```

#### 2. `split_faction` — Interactive swarm splitting

```rust
"split_faction" => {
    let source = cmd.params.get("source_faction").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let new_sub = cmd.params.get("new_sub_faction").and_then(|v| v.as_u64()).unwrap_or(101) as u32;
    let percentage = cmd.params.get("percentage").and_then(|v| v.as_f64()).unwrap_or(0.3) as f32;
    let epi_x = cmd.params.get("epicenter_x").and_then(|v| v.as_f64()).unwrap_or(500.0) as f32;
    let epi_y = cmd.params.get("epicenter_y").and_then(|v| v.as_f64()).unwrap_or(500.0) as f32;

    // Inject as a MacroDirective into the directive executor
    latest_directive.directive = Some(MacroDirective::SplitFaction {
        source_faction: source,
        new_sub_faction: new_sub,
        percentage,
        epicenter: [epi_x, epi_y],
    });
    println!("[WS Command] split_faction {}→{} at ({}, {}) pct={}", source, new_sub, epi_x, epi_y, percentage);
}
```

#### 3. `merge_faction` — Interactive sub-faction merge

```rust
"merge_faction" => {
    let source = cmd.params.get("source_faction").and_then(|v| v.as_u64()).unwrap_or(101) as u32;
    let target = cmd.params.get("target_faction").and_then(|v| v.as_u64()).unwrap_or(0) as u32;

    latest_directive.directive = Some(MacroDirective::MergeFaction {
        source_faction: source,
        target_faction: target,
    });
    println!("[WS Command] merge_faction {}→{}", source, target);
}
```

#### 4. `set_aggro_mask` — Interactive aggro toggle

```rust
"set_aggro_mask" => {
    let source = cmd.params.get("source_faction").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let target = cmd.params.get("target_faction").and_then(|v| v.as_u64()).unwrap_or(1) as u32;
    let allow = cmd.params.get("allow_combat").and_then(|v| v.as_bool()).unwrap_or(true);

    aggro.masks.insert((source, target), allow);
    aggro.masks.insert((target, source), allow);
    println!("[WS Command] set_aggro_mask ({}, {}) allow={}", source, target, allow);
}
```

#### 5. `inject_directive` — Raw ML directive injection for testing

```rust
"inject_directive" => {
    if let Ok(directive) = serde_json::from_value::<MacroDirective>(cmd.params.clone()) {
        latest_directive.directive = Some(directive.clone());
        println!("[WS Command] inject_directive: {:?}", directive);
    }
}
```

#### 6-7. `set_engine_override` / `clear_engine_override` — Tier 1 testing

```rust
"set_engine_override" => {
    let faction = cmd.params.get("faction_id").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let vx = cmd.params.get("velocity_x").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
    let vy = cmd.params.get("velocity_y").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32;
    let ticks = cmd.params.get("ticks").and_then(|v| v.as_u64()).map(|v| v as u32);

    let mut count = 0;
    for (entity, _, _, faction_id, _) in faction_query.iter() {
        if faction_id.0 == faction {
            commands.entity(entity).insert(EngineOverride {
                forced_velocity: Vec2::new(vx, vy),
                ticks_remaining: ticks,
            });
            count += 1;
        }
    }
    println!("[WS Command] set_engine_override faction={} vel=({}, {}) ticks={:?} count={}", faction, vx, vy, ticks, count);
}

"clear_engine_override" => {
    let faction = cmd.params.get("faction_id").and_then(|v| v.as_u64()).unwrap_or(0) as u32;
    let mut count = 0;
    for (entity, _, _, faction_id, _) in faction_query.iter() {
        if faction_id.0 == faction {
            commands.entity(entity).remove::<EngineOverride>();
            count += 1;
        }
    }
    println!("[WS Command] clear_engine_override faction={} count={}", faction, count);
}
```

#### System Parameter Updates

`ws_command_system` needs additional resource parameters:

```rust
pub fn ws_command_system(
    // ... existing params ...
    mut zones: ResMut<ActiveZoneModifiers>,
    mut aggro: ResMut<AggroMaskRegistry>,
    mut latest_directive: ResMut<LatestDirective>,
    // EngineOverride inserts via commands — already available
)
```

### Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - SyncDelta includes zone_modifiers, active_sub_factions, aggro_masks, ml_brain
  - All 7 new WS commands parseable and functional
  - place_zone_modifier adds to ActiveZoneModifiers
  - split_faction / merge_faction inject into LatestDirective
  - Existing WS commands still work (backward compatible)
Suggested_Test_Commands:
  - "cd micro-core && cargo test ws_command"
  - "cd micro-core && cargo test ws_sync"
```

---

## Task 12: Debug Visualizer Frontend Upgrade

**Task_ID:** `task_12_visualizer_phase3`
**Execution_Phase:** 1 (after T11 within Phase 1 chain: T02→T11→T12)
**Model_Tier:** `advanced`
**Target_Files:**
  - `debug-visualizer/index.html` (MODIFY)
  - `debug-visualizer/style.css` (MODIFY)
  - `debug-visualizer/visualizer.js` (MODIFY)
**Dependencies:** Task 11 (WS protocol types for JSON parsing)
**Context_Bindings:**
  - `context/ui-architecture`

### Part A: New UI Panels (`index.html`)

#### 1. ML Brain Status Panel (above Simulation Controls)

```html
<section class="panel-section ml-status">
    <h2>🧠 ML Brain</h2>
    <div class="stats-grid">
        <div class="stat-box">
            <span class="stat-label">Python</span>
            <span id="ml-python-status" class="stat-value mono">—</span>
        </div>
        <div class="stat-box">
            <span class="stat-label">Intervention</span>
            <span id="ml-intervention" class="stat-value mono">—</span>
        </div>
        <div class="stat-box full-width">
            <span class="stat-label">Last Directive</span>
            <span id="ml-last-directive" class="stat-value mono small">—</span>
        </div>
    </div>
</section>
```

#### 2. Zone Modifier Tool (below Terrain Editor)

```html
<section class="panel-section">
    <h2>🧲 Zone Modifiers</h2>
    <div class="controls-row">
        <button id="zone-mode-btn" class="btn secondary">🧲 Place Zone</button>
    </div>
    <div id="zone-tools" style="display: none;">
        <div class="spawn-row">
            <label class="spawn-label">Type</label>
            <div class="zone-type-selector">
                <button class="zone-type-btn active" data-type="attract">🔵 Attract</button>
                <button class="zone-type-btn" data-type="repel">🔴 Repel</button>
            </div>
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Faction</label>
            <select id="zone-faction" class="input-field"></select>
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Radius</label>
            <input type="range" id="zone-radius-slider" min="20" max="300" value="100" class="slider">
            <input type="number" id="zone-radius" class="input-field compact" value="100">
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Intensity</label>
            <input type="range" id="zone-intensity-slider" min="10" max="200" value="50" class="slider">
            <input type="number" id="zone-intensity" class="input-field compact" value="50">
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Duration</label>
            <input type="number" id="zone-duration" class="input-field" value="300" min="1" max="3600">
            <span class="input-suffix">ticks</span>
        </div>
    </div>
    <div id="zone-hint" class="spawn-hint" style="display: none;">
        Click on canvas to place zone modifier
    </div>
</section>
```

#### 3. Faction Splitter Tool (below Zone Modifiers)

```html
<section class="panel-section">
    <h2>✂️ Faction Splitter</h2>
    <div class="controls-row">
        <button id="split-mode-btn" class="btn secondary">✂️ Split Mode</button>
    </div>
    <div id="split-tools" style="display: none;">
        <div class="spawn-row">
            <label class="spawn-label">Source</label>
            <select id="split-source-faction" class="input-field"></select>
        </div>
        <div class="spawn-row">
            <label class="spawn-label">Split %</label>
            <input type="range" id="split-pct-slider" min="5" max="80" value="30" class="slider">
            <input type="number" id="split-pct" class="input-field compact" value="30">
        </div>
    </div>
    <div id="split-hint" class="spawn-hint" style="display: none;">
        Click on canvas to set epicenter
    </div>
    <div id="sub-faction-list" class="sub-faction-list">
        <!-- Populated dynamically from active_sub_factions -->
    </div>
</section>
```

#### 4. Aggro Mask Panel (below Faction Splitter)

```html
<section class="panel-section">
    <h2>🛡️ Aggro Masks</h2>
    <div id="aggro-mask-grid" class="aggro-grid">
        <!-- Populated dynamically: matrix of faction pairs -->
    </div>
</section>
```

#### 5. New Viewport Layer Toggles (extend existing section)

```html
<!-- Add to existing Viewport Layers section -->
<label class="toggle-control">
    <input type="checkbox" id="toggle-density-heatmap">
    <span class="control-indicator"></span>
    <span class="control-label">Density Heatmap</span>
</label>
<label class="toggle-control">
    <input type="checkbox" id="toggle-zone-modifiers" checked>
    <span class="control-indicator"></span>
    <span class="control-label">Zone Modifiers</span>
</label>
<label class="toggle-control">
    <input type="checkbox" id="toggle-override-markers">
    <span class="control-indicator"></span>
    <span class="control-label">Engine Overrides</span>
</label>
```

### Part B: Canvas Rendering (`visualizer.js`)

#### 1. Zone Modifier Circles (on canvas-bg)

```javascript
function drawZoneModifiers(ctx, zoneModifiers, camera) {
    if (!zoneModifiers || !showZoneModifiers) return;

    for (const zone of zoneModifiers) {
        const screenX = (zone.x - camera.x) * camera.zoom + canvas.width / 2;
        const screenY = (zone.y - camera.y) * camera.zoom + canvas.height / 2;
        const screenR = zone.radius * camera.zoom;

        ctx.beginPath();
        ctx.arc(screenX, screenY, screenR, 0, Math.PI * 2);

        if (zone.cost_modifier < 0) {
            // Attract: blue glow with pulsing alpha
            const pulse = 0.3 + 0.2 * Math.sin(Date.now() / 300);
            ctx.fillStyle = `rgba(59, 130, 246, ${pulse})`;
            ctx.strokeStyle = 'rgba(59, 130, 246, 0.7)';
        } else {
            // Repel: red glow
            const pulse = 0.3 + 0.2 * Math.sin(Date.now() / 300);
            ctx.fillStyle = `rgba(239, 68, 68, ${pulse})`;
            ctx.strokeStyle = 'rgba(239, 68, 68, 0.7)';
        }

        ctx.fill();
        ctx.setLineDash([4, 4]);
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.setLineDash([]);

        // Label: cost modifier + remaining ticks
        ctx.fillStyle = '#fff';
        ctx.font = '11px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(
            `${zone.cost_modifier > 0 ? '+' : ''}${zone.cost_modifier} (${zone.ticks_remaining}t)`,
            screenX, screenY
        );
    }
}
```

#### 2. Sub-Faction Color Palette

```javascript
// Extended color palette — base factions + sub-faction gradients
const FACTION_COLORS = {
    0: '#3b82f6',    // Blue (Swarm)
    1: '#ef4444',    // Red (Defenders)
    // Sub-factions: generated dynamically with hue offset
};

function getFactionColor(factionId) {
    if (FACTION_COLORS[factionId]) return FACTION_COLORS[factionId];
    // Sub-factions: derive from parent with hue rotation
    const parent = factionId < 100 ? factionId : Math.floor(factionId / 100) - 1;
    const offset = (factionId % 100) * 30; // 30° hue shift per sub-faction
    const base = parent === 0 ? 220 : 0; // Blue base or Red base
    return `hsl(${(base + offset) % 360}, 70%, 55%)`;
}
```

#### 3. Density Heatmap Overlay (on canvas-bg, semi-transparent)

```javascript
function drawDensityHeatmap(ctx, density, gridW, gridH, cellSize, camera) {
    if (!density || !showDensityHeatmap) return;

    for (let y = 0; y < gridH; y++) {
        for (let x = 0; x < gridW; x++) {
            const value = density[y * gridW + x];
            if (value < 0.01) continue; // Skip empty cells

            const worldX = x * cellSize;
            const worldY = y * cellSize;
            const screenX = (worldX - camera.x) * camera.zoom + canvas.width / 2;
            const screenY = (worldY - camera.y) * camera.zoom + canvas.height / 2;
            const screenSize = cellSize * camera.zoom;

            // Heat gradient: transparent → yellow → orange → red
            const alpha = Math.min(value * 0.6, 0.6);
            const hue = 60 - value * 60; // 60=yellow → 0=red
            ctx.fillStyle = `hsla(${hue}, 100%, 50%, ${alpha})`;
            ctx.fillRect(screenX, screenY, screenSize, screenSize);
        }
    }
}
```

#### 4. EngineOverride Entity Markers

```javascript
// In entity rendering loop — if entity has EngineOverride, draw diamond marker
function drawEntity(ctx, entity, camera) {
    // ... existing circle drawing ...

    // Override marker: flashing diamond outline
    if (entity.has_override) {
        const t = Date.now() / 200;
        ctx.strokeStyle = `rgba(255, 215, 0, ${0.5 + 0.5 * Math.sin(t)})`;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(screenX, screenY - 6);
        ctx.lineTo(screenX + 6, screenY);
        ctx.lineTo(screenX, screenY + 6);
        ctx.lineTo(screenX - 6, screenY);
        ctx.closePath();
        ctx.stroke();
    }
}
```

#### 5. ML Brain Status Updates

```javascript
function updateMlBrainPanel(mlBrain) {
    if (!mlBrain) return;

    const pythonEl = document.getElementById('ml-python-status');
    const interventionEl = document.getElementById('ml-intervention');
    const directiveEl = document.getElementById('ml-last-directive');

    pythonEl.textContent = mlBrain.python_connected ? '🟢 Connected' : '🔴 Disconnected';
    pythonEl.style.color = mlBrain.python_connected ? '#22c55e' : '#ef4444';

    interventionEl.textContent = mlBrain.intervention_active ? '⚠️ Active' : '✅ Normal';
    interventionEl.style.color = mlBrain.intervention_active ? '#f59e0b' : '#22c55e';

    if (mlBrain.last_directive) {
        try {
            const d = JSON.parse(mlBrain.last_directive);
            directiveEl.textContent = d.directive || 'Hold';
        } catch {
            directiveEl.textContent = '—';
        }
    }
}
```

#### 6. Aggro Mask Matrix

```javascript
function updateAggroGrid(aggroMasks, activeFactions) {
    const container = document.getElementById('aggro-mask-grid');
    container.innerHTML = '';

    for (const mask of aggroMasks) {
        const cell = document.createElement('div');
        cell.className = `aggro-cell ${mask.allow_combat ? 'combat-on' : 'combat-off'}`;
        cell.innerHTML = `
            <span class="aggro-label">${mask.source_faction}→${mask.target_faction}</span>
            <span class="aggro-icon">${mask.allow_combat ? '⚔️' : '🛡️'}</span>
        `;
        cell.onclick = () => sendCommand('set_aggro_mask', {
            source_faction: mask.source_faction,
            target_faction: mask.target_faction,
            allow_combat: !mask.allow_combat,
        });
        container.appendChild(cell);
    }
}
```

#### 7. Interactive Canvas Modes

Extend the existing mode system (`spawnMode`, `paintMode`) with:

- **`zoneMode`**: Click canvas → `place_zone_modifier` at click position with current tool settings
  - While in zone mode, draw a radius preview circle following the cursor
  - Preview circle color changes based on attract (blue) vs repel (red) setting
- **`splitMode`**: Click canvas → `split_faction` with click position as epicenter
  - While in split mode, draw a crosshair at cursor + show "X% of FactionN" tooltip

### Part C: Legend & Color Updates

```html
<!-- Dynamic legend populated from active_sub_factions -->
<div class="legend-list" id="legend-list">
    <!-- Base factions (always shown) -->
    <div class="legend-item">
        <span class="color-swatch" style="background: #3b82f6;"></span>
        <span>Faction 0 (Swarm)</span>
    </div>
    <div class="legend-item">
        <span class="color-swatch" style="background: #ef4444;"></span>
        <span>Faction 1 (Defenders)</span>
    </div>
    <!-- Sub-factions added dynamically -->
</div>
```

```javascript
function updateLegend(activeSubFactions) {
    const legend = document.getElementById('legend-list');
    // Keep base factions, remove old sub-faction entries
    legend.querySelectorAll('.legend-sub').forEach(el => el.remove());

    for (const sf of (activeSubFactions || [])) {
        const item = document.createElement('div');
        item.className = 'legend-item legend-sub';
        item.innerHTML = `
            <span class="color-swatch" style="background: ${getFactionColor(sf)};"></span>
            <span>Sub-Faction ${sf}</span>
        `;
        legend.appendChild(item);
    }
}
```

---

## Summary: Complete Tool Matrix

| Dev Scenario | Tool | Where |
|-------------|------|-------|
| "Why are entities clustering here?" | Density heatmap overlay | Toggle: Viewport Layers |
| "I want to attract entities to a point" | Zone Modifier tool (click-to-place) | Panel: Zone Modifiers |
| "I need to split the swarm for testing" | Faction Splitter (click epicenter) | Panel: Faction Splitter |
| "I want to reunite a sub-faction" | Merge button per sub-faction | Panel: Faction Splitter → sub-faction list |
| "Are these factions fighting?" | Aggro mask matrix (click to toggle) | Panel: Aggro Masks |
| "Is Python connected?" | ML Brain status | Panel: ML Brain |
| "What did the AI just do?" | Last directive display | Panel: ML Brain |
| "Is the engine overriding entities?" | Intervention flag + entity markers | Panel: ML Brain + Toggle: Engine Overrides |
| "I want to test a specific directive" | Raw directive injection | WS Command: inject_directive |
| "Which entities are sub-faction 101?" | Sub-faction color palette | Automatic (entity rendering) |
| "How does the terrain cost look after zone modifiers?" | Zone modifier circles with cost labels | Toggle: Zone Modifiers |
| "I need to test the EngineOverride system" | Faction-level override inject/clear | WS Commands |

---

## Verification_Strategy

```
Test_Type: unit (Rust) + manual (browser)
Test_Stack: cargo test (Rust) + browser visual inspection
Acceptance_Criteria:
  Rust Side:
    - WS broadcast includes all new fields when debug-telemetry enabled
    - All 7 new WS commands are functional
    - Backward compatible with existing commands
  Frontend:
    - Zone modifier circles render with correct position, radius, color
    - Density heatmap overlay shows heat gradient
    - Sub-faction entities rendered with distinct colors
    - ML Brain panel shows connection status and last directive
    - Aggro mask matrix is interactive (click to toggle)
    - Zone mode: cursor preview circle + click-to-place
    - Split mode: click-to-set-epicenter + percentage slider
    - Legend updates dynamically with active sub-factions
    - EngineOverride entities have flashing diamond marker
Suggested_Test_Commands:
  - "cd micro-core && cargo test ws_command"
  - "cd micro-core && cargo test ws_sync"
  - "Open debug-visualizer/index.html, start Rust core, visually verify all panels"
```
