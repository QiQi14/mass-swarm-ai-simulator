# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_15_integration` |
| Feature | Debug Visualizer UX Refactor |
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

1. **Create** `tasks_pending/task_15_integration_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_15_integration
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

- `./.agents/skills/rust-code-standards/SKILL.md`
- `implementation_plan.md` → Feature 4: State Management + all feature sections` _(not found — verify path)_

---

## Task Brief

# Task 15 — Integration: Resource Registration + System Gating + Smoke Test

## Metadata
- **Task_ID:** task_15_integration
- **Execution_Phase:** Phase 4 — Final Integration (sequential, depends on ALL)
- **Model_Tier:** advanced
- **Dependencies:**
  - Task 09 (TerrainGrid)
  - Task 10 (FactionVisibility, VisionRadius)
  - Task 11 (Flow Field + Movement terrain integration)
  - Task 12 (Visibility system + IPC)
  - Task 13 (WS Commands)
  - Task 14 (Visualizer UI)
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 4: State Management + all feature sections

## Target Files
- `micro-core/src/main.rs` — **MODIFY** (resource registration, system scheduling, state gating)

## Contract: SimState Gating + Resource Wiring

### Resource Registration
All new resources must be registered in `main.rs` App builder:

```rust
// TerrainGrid (Task 09) — matches flow field dimensions
let cell_size = 20.0;
let grid_w = (1000.0 / cell_size).ceil() as u32;  // 50
let grid_h = (1000.0 / cell_size).ceil() as u32;  // 50
app.insert_resource(TerrainGrid::new(grid_w, grid_h, cell_size));

// FactionVisibility (Task 10)
app.insert_resource(FactionVisibility::new(grid_w, grid_h, cell_size));

// ActiveFogFaction (Task 12)
app.insert_resource(ActiveFogFaction(None));
```

VisionRadius is a Component — no resource registration needed, but it MUST be added to all entity spawn bundles (`wave_spawn_system`, `ws_command spawn_wave`, etc).

### System Scheduling with SimState Gating

| System | Schedule | run_if |
|--------|----------|--------|
| `ws_command_system` | Update | Always (no gate) |
| `ws_sync_system` | Update | Always (no gate) |
| `visibility_update_system` | Update | Always (no gate) |
| `flow_field_update_system` | Update | Always (no gate) |
| `movement_system` | Update | `in_state(SimState::Running)` |
| `interaction_system` | Update | `in_state(SimState::Running)` |
| `removal_system` | Update | `in_state(SimState::Running)` |
| `wave_spawn_system` | Update | `in_state(SimState::Running)` |

### Visualizer starts Paused
The app should initialize with `SimState::Setup` (or equivalent paused state) so the user can design terrain and place units before pressing Play.

## Strict Instructions

### 1. Modify `micro-core/src/main.rs`

**a. Add imports:**
```rust
use crate::terrain::TerrainGrid;
use crate::visibility::FactionVisibility;
// ActiveFogFaction from wherever Task 12 defined it
```

**b. Register resources** as described above.

**c. Add `visibility_update_system` to the system schedule** (always runs).

**d. Gate physics systems** with `run_if(in_state(SimState::Running))`:
- `movement_system`
- `interaction_system`
- `removal_system`
- `wave_spawn_system`

**e. Ensure ws_command, ws_sync, flow_field_update, visibility_update run WITHOUT state gates** (must work while paused for terrain painting and fog preview).

**f. Add `VisionRadius::default()` to ALL entity spawn bundles** — check `wave_spawn_system` and any initial entity spawning in `main.rs`.

### 2. Build + Test

After modifications:
```bash
cd micro-core && cargo build    # Must compile
cd micro-core && cargo test     # All tests pass
./dev.sh --smoke                # 300-tick smoke test clean exit
```

## Verification Strategy

**Test_Type:** integration
**Test_Stack:** `cargo test` + `./dev.sh --smoke` + browser

**Acceptance Criteria:**
1. `cargo build` succeeds with no errors
2. `cargo test` — all tests pass (including new terrain, visibility, flow field tests)
3. `./dev.sh --smoke` — 300 ticks, clean shutdown
4. `./dev.sh` + browser at `http://127.0.0.1:3000`:
   - Paint terrain while paused → terrain visible in browser
   - Spawn units while paused → entities appear
   - Press Play → entities move, respecting terrain (wall-sliding, speed reduction)
   - Toggle fog → fog overlay renders correctly
   - Save scenario → download JSON
   - Load scenario → state restored
5. `cargo build --no-default-features` — production build compiles without telemetry

**Commands:**
```bash
cd micro-core && cargo build
cd micro-core && cargo test
cd micro-core && cargo build --no-default-features
./dev.sh --smoke
./dev.sh  # Manual browser testing
```

---

## Shared Contracts

# Debug Visualizer UX Refactor — Mass Spawn, Fog of War, Terrain Editor

## Overview

Three cross-cutting features to make the debug visualizer a proper simulation laboratory.

### Core Principles
- **Contract-based:** Rust core deals ONLY with numeric weights and vision radii. Named types exist ONLY in JS.
- **Self-contained:** FoW and terrain live in the Rust core. ML brain works without visualizer.
- **Setup→Run workflow:** Visualizer starts in `SimState::Setup`. User designs → presses Play → `SimState::Running`.
- **Integer-only hot paths:** No floating-point in Dijkstra inner loop. No division in tick-hot systems.

---

## Inter-Layer Architecture — How FoW Feeds the ML Brain

The simulator has **three layers** connected by two IPC channels with **different data fidelity**:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RUST MICRO-CORE (Ground Truth)                   │
│                                                                         │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ All Entity │  │ TerrainGrid  │  │ FactionVis   │  │  FlowField   │  │
│  │ Positions  │  │ hard + soft  │  │ explored +   │  │  Registry    │  │
│  │ (omniscient│  │ costs        │  │ visible per  │  │              │  │
│  │  ECS World)│  │              │  │ faction      │  │              │  │
│  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │
│        │                │                  │                             │
│   ┌────┴────────────────┴──────────────────┴────┐                       │
│   │          DATA FILTER CONTRACTS              │                       │
│   │                                            │                       │
│   │  Channel A: ZMQ → Python Brain             │                       │
│   │  ─────────────────────────────             │                       │
│   │  FILTERED by FoW. Brain is NOT omniscient. │                       │
│   │  • own_entities: ALL own faction entities  │                       │
│   │  • visible_enemies: ONLY enemies in        │                       │
│   │    faction's VISIBLE cells                 │                       │
│   │  • explored_grid: bit-packed (what I know) │                       │
│   │  • visible_grid: bit-packed (what I see)   │                       │
│   │  • terrain: FULL grid (terrain is public)  │                       │
│   │                                            │                       │
│   │  Channel B: WebSocket → JS Debug Visualizer│                       │
│   │  ──────────────────────────────────────     │                       │
│   │  UNFILTERED. Debug tool sees everything.   │                       │
│   │  • All entities (omniscient for debugging) │                       │
│   │  • FoW overlay = OPTIONAL visual layer     │                       │
│   │  • Terrain + Flow field arrows             │                       │
│   │  • Telemetry (perf bars, tick counter)      │                       │
│   └─────────────────────────────────────────────┘                       │
└───────────────┬──────────────────────────┬──────────────────────────────┘
                │                          │
       ZMQ REQ/REP (~2 TPS)        WebSocket (60 TPS entities,
       Fog-filtered snapshot         10 TPS fog, feature-gated)
                │                          │
                ▼                          ▼
┌──────────────────────────┐  ┌────────────────────────────────┐
│   PYTHON MACRO-BRAIN     │  │  JS DEBUG VISUALIZER (Browser) │
│                          │  │                                │
│ Observation Space:       │  │ Omniscient view:               │
│ • I see 200 enemies      │  │ • All 10,000 entities visible  │
│   (3000 hidden by fog)   │  │ • FoW overlay shows what a     │
│ • I know 60% of map      │  │   faction WOULD see            │
│   (explored grid)        │  │ • Terrain grid painted by user │
│ • Terrain is fully known │  │ • Flow field arrows visible    │
│                          │  │                                │
│ Decision Output:         │  │ Controls:                      │
│ • MacroAction (HOLD,     │  │ • Spawn units, paint terrain   │
│   FLANK_LEFT, RETREAT)   │  │ • Toggle fog per faction       │
│                          │  │ • Save/Load scenarios          │
└──────────────────────────┘  └────────────────────────────────┘
```

### Key Data Flow Contracts

| Data | ZMQ → Python Brain | WS → JS Visualizer |
|------|:-:|:-:|
| Own faction entities | ✅ Always (full stats) | ✅ Always |
| Enemy entities | ⚠️ **Only if in VISIBLE cells** | ✅ Always (debug omniscient) |
| Explored grid (bit-packed) | ✅ Faction's own grid | ✅ Selected faction's grid |
| Visible grid (bit-packed) | ✅ Faction's own grid | ✅ Selected faction's grid |
| Terrain grid | ✅ Full (terrain is public info) | ✅ Full |
| Telemetry / perf data | ❌ Never (Python doesn't need it) | ✅ Feature-gated |
| Flow field arrows | ❌ Never (brain makes its own decisions) | ✅ Optional overlay |

### ZMQ Integration Change

The existing `build_state_snapshot()` in [systems.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_bridge/systems.rs) currently sends **ALL entities omnisciently**. This must be refactored:

#### [MODIFY] [zmq_bridge/systems.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_bridge/systems.rs) — FoW-Filtered Snapshot

```rust
fn build_state_snapshot(
    tick: &TickCounter,
    sim_config: &SimulationConfig,
    query: &Query<(&EntityId, &Position, &FactionId, &StatBlock)>,
    visibility: &FactionVisibility,      // NEW: fog data
    terrain: &TerrainGrid,               // NEW: terrain data
    brain_faction: u32,                  // NEW: which faction this brain controls
) -> StateSnapshot {
    let vis_grid = visibility.visible.get(&brain_faction);
    let exp_grid = visibility.explored.get(&brain_faction);

    let mut entities = Vec::new();
    for (eid, pos, faction, stat_block) in query.iter() {
        if faction.0 == brain_faction {
            // OWN ENTITIES: always visible to self
            entities.push(EntitySnapshot { /* ... */ });
        } else if let Some(vg) = vis_grid {
            // ENEMY ENTITIES: only if in a VISIBLE cell
            let cell_idx = pos_to_cell_index(pos, visibility);
            if FactionVisibility::get_bit(vg, cell_idx) {
                entities.push(EntitySnapshot { /* ... */ });
            }
            // Enemies in fog are INVISIBLE to the brain
        }
    }

    StateSnapshot {
        entities,
        // NEW FIELDS:
        explored: exp_grid.cloned(),     // What the brain has explored
        visible: vis_grid.cloned(),       // What the brain currently sees
        terrain_hard: terrain.hard_costs.clone(),
        terrain_soft: terrain.soft_costs.clone(),
        // ... existing fields ...
    }
}
```

#### [MODIFY] [zmq_protocol.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/zmq_protocol.rs) — Extended Protocol

```rust
pub struct StateSnapshot {
    pub msg_type: String,
    pub tick: u64,
    pub world_size: WorldSize,
    pub entities: Vec<EntitySnapshot>,   // FoW-filtered — brain sees only visible enemies
    pub summary: SummarySnapshot,
    // NEW: Fog of War data for the brain's faction
    pub explored: Option<Vec<u32>>,      // Bit-packed explored grid
    pub visible: Option<Vec<u32>>,       // Bit-packed visible grid
    // NEW: Terrain data (always full — terrain is public knowledge)
    pub terrain_hard: Vec<u16>,
    pub terrain_soft: Vec<u16>,
    pub terrain_grid_w: u32,
    pub terrain_grid_h: u32,
    pub terrain_cell_size: f32,
}
```

> [!IMPORTANT]
> **The brain is NOT omniscient.** Before this change, `build_state_snapshot()` sent ALL 10,000 entities to Python. After this change, a brain controlling faction 0 sees its own 5,000 entities + only the ~200 enemy entities that are within its VISIBLE cells. The remaining ~4,800 enemies are hidden behind fog. **This creates information asymmetry — the core strategic constraint for ML training.**

> [!WARNING]
> **Terrain IS public.** Unlike entities, terrain weights are fully visible to all factions (you can see a mountain even in fog — it's static geography). The brain receives the complete terrain grid every snapshot.

---

## Feature 1: Mass Spawn Controls (Fibonacci Spiral)

**Scope:** JS/HTML + Rust `spawn_wave` refactor.

### Current Problem
`visualizer.js:290`: hardcoded `faction_id: 0, amount: 10`. No spread. Random placement would cause Boids supernova.

### Architecture: Fibonacci Spiral Packing

Naive random spawning (`r = spread * rand()`) causes center-clumping (circle area scales quadratically).
Worse, overlapping positions create astronomically high Boids inverse-square repulsion → fragmentation grenade on frame 1.

**Solution:** Fibonacci Spiral with `sqrt()` area distribution — mathematically equidistant packing.

```rust
// micro-core/src/systems/ws_command.rs → spawn_wave handler
let golden_angle = 137.5f32.to_radians();

for i in 0..amount {
    // sqrt() ensures uniform AREA distribution, preventing center-clumping
    let r = spread * (i as f32 / amount as f32).sqrt();
    let theta = i as f32 * golden_angle;
    
    let spawn_x = x + r * theta.cos();
    let spawn_y = y + r * theta.sin();
    
    // Skip wall cells — don't spawn inside terrain
    let cell = IVec2::new(
        (spawn_x / terrain.cell_size).floor() as i32,
        (spawn_y / terrain.cell_size).floor() as i32,
    );
    if terrain.get_hard_cost(cell) == u16::MAX { continue; }
    
    commands.spawn(( /* entity bundle */ ));
}
```

### Proposed Changes

#### [MODIFY] [index.html](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/debug-visualizer/index.html)
Add **Spawn Tools** section:
- Faction dropdown (populated from `ADAPTER_CONFIG`)
- Amount: slider (1–500) synced with number input
- Spread radius: slider (0–100) synced with number input

#### [MODIFY] [visualizer.js](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/debug-visualizer/visualizer.js)
- Read spawn controls on canvas click
- Show ghost circle at cursor (radius = spread) while hovering
- Send: `sendCommand("spawn_wave", { faction_id, amount, x, y, spread })`

#### [MODIFY] [ws_command.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/ws_command.rs)
- Replace random scatter with Fibonacci Spiral
- Skip wall cells during spawn
- Add `spread` param (default 0 = single-point, backward compatible)

---

## Feature 2: Fog of War (Core Resource, Bit-Packed, Wall-Aware)

**Scope:** Rust core + JS visualizer. First-class simulation resource for ML.

### Architecture

```
Rust Core (Contract-Based)                 JS Visualizer
┌────────────────────────────────┐         ┌───────────────────┐
│ VisionRadius component         │         │ Per-faction toggle │
│ (per-entity, default 80.0)     │         │                   │
│                                │  WS     │ Render layers:    │
│ FactionVisibility resource     │ 10 TPS  │ 1. Unexplored=■   │
│   explored: HashMap<u32,       │────────►│ 2. Explored  =▓   │
│     Vec<u32>> (bit-packed)     │ ~350B   │ 3. Visible   =□   │
│   visible:  HashMap<u32,       │         │                   │
│     Vec<u32>> (bit-packed)     │         │ Offscreen canvas  │
│                                │         │ compositing       │
│ visibility_update_system       │         └───────────────────┘
│ (every tick, cell-deduplicated)│
│ (wall-aware: no X-ray vision) │
└────────────────────────────────┘
```

### Anti-Patterns Addressed

| Problem | Solution |
|---------|----------|
| `Vec<bool>` JSON = 15KB/faction/frame | Bit-packed `Vec<u32>`: 2500 bits = 79 integers = **~350 bytes** |
| 60 FPS sync = 1 MB/s bandwidth | Throttle VisibilitySync to **10 TPS** |
| 5000 entities in chokepoint → 5000× redundant cell writes | **Cell-centric deduplication**: group by grid cell, calc once per occupied cell |
| Mathematical radius ignores walls → X-ray vision | **Wall-aware**: cast through terrain grid, stop at `hard_cost == MAX` |

### Proposed Changes

#### [NEW] `micro-core/src/components.rs` — Add `VisionRadius`
```rust
/// Per-entity vision radius in world units.
/// Determines fog of war explored/visible area for the entity's faction.
#[derive(Component, Debug, Clone)]
pub struct VisionRadius(pub f32);

impl Default for VisionRadius {
    fn default() -> Self { Self(80.0) }
}
```

#### [NEW] `micro-core/src/visibility.rs`

```rust
/// Per-faction visibility state. Self-contained — works without visualizer.
///
/// ## Bit-Packing
/// A 50×50 grid = 2,500 cells. Stored as Vec<u32> where each u32 holds
/// 32 cells. Total: ceil(2500/32) = 79 integers per faction.
///
/// ## Cell-Centric Deduplication
/// Instead of iterating entities (O(E × vision_cells)), we:
/// 1. Group entities into grid cells           — O(E)
/// 2. Deduplicate to unique occupied cells      — O(cells)
/// 3. Calculate vision per occupied cell         — O(cells × vision_cells)
/// At 10K entities in ~200 unique cells → 200 × 49 = 9,800 cell checks vs 490,000.
///
/// ## Wall-Aware Vision
/// Vision does not penetrate walls (hard_cost == u16::MAX).
/// Uses a simple cell-adjacency flood within vision radius — cells behind
/// walls are never marked visible.
#[derive(Resource, Debug, Clone)]
pub struct FactionVisibility {
    pub grid_width: u32,
    pub grid_height: u32,
    pub cell_size: f32,
    /// explored[faction_id] = bit-packed grid of EVER-seen cells
    pub explored: HashMap<u32, Vec<u32>>,
    /// visible[faction_id] = bit-packed grid of CURRENTLY-seen cells
    pub visible: HashMap<u32, Vec<u32>>,
}

impl FactionVisibility {
    // Bit manipulation helpers
    pub fn set_bit(grid: &mut [u32], index: usize) {
        grid[index / 32] |= 1 << (index % 32);
    }
    pub fn get_bit(grid: &[u32], index: usize) -> bool {
        (grid[index / 32] >> (index % 32)) & 1 == 1
    }
    pub fn clear_all(grid: &mut [u32]) {
        grid.iter_mut().for_each(|v| *v = 0);
    }
}
```

#### [NEW] `micro-core/src/systems/visibility.rs`

```rust
/// Updates per-faction visible and explored grids.
/// Runs every tick. Cell-centric deduplication + wall-aware flood.
pub fn visibility_update_system(
    mut visibility: ResMut<FactionVisibility>,
    terrain: Res<TerrainGrid>,
    query: Query<(&Position, &FactionId, &VisionRadius)>,
) {
    // 1. Clear all visible grids (transient — rebuilt each tick)
    for grid in visibility.visible.values_mut() {
        FactionVisibility::clear_all(grid);
    }

    // 2. Group entities into grid cells, deduplicate per faction
    //    Key: (faction_id, cell_x, cell_y) → max vision radius in that cell
    let mut occupied: HashMap<(u32, i32, i32), f32> = HashMap::default();
    for (pos, faction, vision) in query.iter() {
        let cx = (pos.x / visibility.cell_size).floor() as i32;
        let cy = (pos.y / visibility.cell_size).floor() as i32;
        let entry = occupied.entry((faction.0, cx, cy)).or_insert(0.0);
        *entry = entry.max(vision.0); // Keep largest vision radius
    }

    // 3. For each unique (faction, cell), flood-fill within vision radius
    //    Wall-aware: skip cells where terrain hard_cost == u16::MAX
    for (&(faction_id, cx, cy), &vision_r) in &occupied {
        let cell_radius = (vision_r / visibility.cell_size).ceil() as i32;
        let vis_grid = visibility.visible
            .entry(faction_id)
            .or_insert_with(|| vec![0u32; bitpack_size(visibility)]);
        let exp_grid = visibility.explored
            .entry(faction_id)
            .or_insert_with(|| vec![0u32; bitpack_size(visibility)]);

        for dy in -cell_radius..=cell_radius {
            for dx in -cell_radius..=cell_radius {
                let nx = cx + dx;
                let ny = cy + dy;
                if nx < 0 || ny < 0
                    || nx >= visibility.grid_width as i32
                    || ny >= visibility.grid_height as i32 { continue; }

                // Wall-aware: don't see through walls
                let cell = IVec2::new(nx, ny);
                if terrain.get_hard_cost(cell) == u16::MAX { continue; }

                // Distance check (in cells)
                if (dx * dx + dy * dy) as f32 <= (cell_radius as f32).powi(2) {
                    let idx = (ny as u32 * visibility.grid_width + nx as u32) as usize;
                    FactionVisibility::set_bit(vis_grid, idx);
                    FactionVisibility::set_bit(exp_grid, idx);
                }
            }
        }
    }
}
```

#### [MODIFY] [ws_sync.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/ws_sync.rs)
Add VisibilitySync to SyncDelta (feature-gated, **throttled to 10 TPS**):
```rust
#[cfg(feature = "debug-telemetry")]
visibility: Option<VisibilitySync>,
// Only populated every 6th tick (60/6 = 10 TPS)
// Only for the active fog faction (set by "set_fog_faction" command)
```

#### [MODIFY] [ws_protocol.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/bridges/ws_protocol.rs)
```rust
#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisibilitySync {
    pub faction_id: u32,
    pub explored: Vec<u32>,  // Bit-packed: 79 integers for 50×50
    pub visible: Vec<u32>,   // Bit-packed: 79 integers for 50×50
}
```

#### [MODIFY] [index.html](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/debug-visualizer/index.html)
Replace single `toggle-fog` with per-faction toggles (only one active at a time — radio behavior):
```html
<label class="toggle-control">
    <input type="checkbox" id="toggle-fog-0">
    <span class="control-indicator" style="border-color:#ff3b30"></span>
    <span class="control-label">Swarm Fog</span>
</label>
<label class="toggle-control">
    <input type="checkbox" id="toggle-fog-1">
    <span class="control-indicator" style="border-color:#0a84ff"></span>
    <span class="control-label">Defender Fog</span>
</label>
```

#### [MODIFY] [visualizer.js](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/debug-visualizer/visualizer.js)
- Bit-unpacking helpers for `Vec<u32>` fog data
- Offscreen canvas compositing: unexplored=black, explored-only=dim, visible=clear
- On fog toggle change: send `set_fog_faction` command to Rust core

---

## Feature 3: Terrain Editor (Integer Dual-Weight)

**Scope:** Cross-cutting — JS UI + WS commands + Rust resource + flow field + movement integration.

### Core Design: Inverted Integer Cost Model

The Rust core uses **inverted integer multipliers** — no floats in Dijkstra.

```
                 Core Contract                         UI Mapping
                 ─────────────                         ──────────
                 hard_cost (u16)    soft_cost (u16)    Brush
                 ──────────────    ──────────────     ─────
Wall:            u16::MAX (∞)      0                  ⬛ Wall
Mud:             200 (2× cost)     30 (30% speed)     🟫 Mud
Pushable:        125 (1.25× cost)  50 (50% speed)     🟧 Pushable
Clear:           100 (normal)      100 (full speed)   ⬜ Clear

hard_cost: Dijkstra cost multiplier. Pure integer: (move_cost × hard_cost) / 100
  → 100 = normal cost
  → 200 = 2× cost (mud — paths strongly avoid)
  → 125 = 1.25× cost (pushable — paths mildly avoid)
  → u16::MAX = absolute wall (skipped entirely in BFS queue)

soft_cost: Movement speed percentage (0–100 scale)
  → 100 = full speed
  → 50 = 50% speed (pushable terrain)
  → 30 = 30% speed (mud)
  → 0 = frozen (but kinematic wall-sliding prevents getting stuck)
```

### Anti-Patterns Addressed

| Problem | Solution |
|---------|----------|
| `move_cost / hard_weight` → div-by-zero at 0.0 | `hard_cost == u16::MAX → continue` (skip entirely) |
| Float division in Dijkstra inner loop | Pure integer: `(move_cost * hard_cost) / 100` |
| Integer truncation (12.5→12) | Multiplier scale 100 preserves precision |
| Entity pushed into wall → `speed × 0.0 = 0` → permanent paralysis | **Kinematic Wall-Sliding**: per-axis velocity zeroing |

### Proposed Changes

#### [NEW] `micro-core/src/terrain.rs`

```rust
/// Paintable terrain weight grid. Contract-based — core sees only integers.
///
/// ## Inverted Integer Cost Model
/// - `hard_costs`: Dijkstra cost multiplier (scale 100).
///   100 = normal, 200 = double cost, u16::MAX = impassable wall.
///   Formula: `effective_cost = (movement_cost × hard_cost) / 100`
/// - `soft_costs`: Movement speed percentage (0–100).
///   100 = full speed, 50 = half speed, 0 = stopped.
///   Formula: `effective_speed = max_speed × soft_cost / 100`
///
/// ## Dimensions
/// Grid matches flow field: ceil(world_size / cell_size).
/// Default cell_size = 20.0 → 50×50 grid for 1000×1000 world.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct TerrainGrid {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    pub hard_costs: Vec<u16>,  // [y * width + x], default 100
    pub soft_costs: Vec<u16>,  // [y * width + x], default 100
}

impl TerrainGrid {
    pub fn new(width: u32, height: u32, cell_size: f32) -> Self {
        let size = (width * height) as usize;
        Self {
            width, height, cell_size,
            hard_costs: vec![100u16; size],
            soft_costs: vec![100u16; size],
        }
    }

    pub fn get_hard_cost(&self, cell: IVec2) -> u16 {
        if !self.in_bounds(cell) { return u16::MAX; }  // OOB = wall
        self.hard_costs[(cell.y as u32 * self.width + cell.x as u32) as usize]
    }

    pub fn get_soft_cost(&self, cell: IVec2) -> u16 {
        if !self.in_bounds(cell) { return 0; }  // OOB = frozen
        self.soft_costs[(cell.y as u32 * self.width + cell.x as u32) as usize]
    }

    pub fn set_cell(&mut self, x: u32, y: u32, hard: u16, soft: u16) {
        if x < self.width && y < self.height {
            let idx = (y * self.width + x) as usize;
            self.hard_costs[idx] = hard;
            self.soft_costs[idx] = soft;
        }
    }

    /// Returns cells with hard_cost == u16::MAX as IVec2 obstacles.
    pub fn hard_obstacles(&self) -> Vec<IVec2> {
        let mut obs = Vec::new();
        for y in 0..self.height {
            for x in 0..self.width {
                if self.hard_costs[(y * self.width + x) as usize] == u16::MAX {
                    obs.push(IVec2::new(x as i32, y as i32));
                }
            }
        }
        obs
    }

    fn in_bounds(&self, cell: IVec2) -> bool {
        cell.x >= 0 && cell.x < self.width as i32
            && cell.y >= 0 && cell.y < self.height as i32
    }
}
```

#### [MODIFY] [flow_field.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/pathfinding/flow_field.rs) — Integer Cost Map

New `calculate()` signature:
```rust
pub fn calculate(
    &mut self,
    goals: &[Vec2],
    obstacles: &[IVec2],
    cost_map: Option<&[u16]>,  // Inverted integer costs (100=normal, u16::MAX=wall)
)
```

Inner Dijkstra loop (100% integer math):
```rust
for &(dx, dy, move_cost) in &NEIGHBORS_8 {
    let neighbor = IVec2::new(cell.x + dx, cell.y + dy);
    if !self.in_bounds(neighbor) || obstacle_set.contains(&neighbor) { continue; }

    // Anti-corner-cutting (unchanged)
    if move_cost == 14 { /* ... existing check ... */ }

    // ── NEW: Terrain cost integration (pure integer) ──
    let terrain_penalty = cost_map
        .map(|cm| cm[self.cell_index(neighbor)])
        .unwrap_or(100);

    // Absolute wall — skip entirely (never enters BFS queue)
    if terrain_penalty == u16::MAX { continue; }

    // Integer math: (10 × 200) / 100 = 20 (double cost for mud)
    let effective_cost = (move_cost * terrain_penalty as u32) / 100;
    let next_cost = cost.saturating_add(effective_cost);

    // ... rest of Dijkstra unchanged ...
}
```

> [!IMPORTANT]
> `cost_map: Option` means ALL existing callers and tests work with `None` (backward compatible). When `Some`, costs scale by terrain. When `u16::MAX`, cell is treated as absolute wall — never enters the BFS queue.

#### [MODIFY] [flow_field_update.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/flow_field_update.rs)
```diff
- field.calculate(goals, &[]);
+ field.calculate(goals, &terrain.hard_obstacles(), Some(&terrain.hard_costs));
```

#### [MODIFY] [movement.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/movement.rs) — Kinematic Wall-Sliding

```rust
// After computing desired next_x, next_y from velocity:

let world_to_cell = |x: f32, y: f32| -> IVec2 {
    IVec2::new(
        (x / terrain.cell_size).floor() as i32,
        (y / terrain.cell_size).floor() as i32,
    )
};

// ── Kinematic Wall-Sliding ──
// Check X and Y axes INDEPENDENTLY to allow sliding along walls.
// This prevents the "quicksand trap" where soft_cost=0 freezes the entity.
if terrain.get_hard_cost(world_to_cell(next_x, pos.y)) == u16::MAX {
    vel.dx = 0.0;
    next_x = pos.x;  // Blocked on X — slide vertically
}
if terrain.get_hard_cost(world_to_cell(pos.x, next_y)) == u16::MAX {
    vel.dy = 0.0;
    next_y = pos.y;  // Blocked on Y — slide horizontally
}

// ── Soft terrain speed modifier ──
let cell = world_to_cell(next_x, next_y);
let soft = terrain.get_soft_cost(cell) as f32 / 100.0;
let effective_speed = mc.max_speed * soft;  // 50 = half speed, 100 = full
```

#### [MODIFY] [ws_command.rs](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core/src/systems/ws_command.rs)

New terrain commands:
```rust
"set_terrain" => {
    // { cells: [{ x, y, hard, soft }, ...] }
    // Batch update terrain cells
    // Set terrain_dirty flag → triggers flow field recalc
}
"clear_terrain" => {
    // Reset all costs to (hard=100, soft=100)
    // Set terrain_dirty flag
}
"load_scenario" => {
    // { terrain: { hard_costs, soft_costs }, entities: [{id, x, y, faction, stats}] }
    // 1. Despawn all existing entities
    // 2. Apply terrain grid
    // 3. Spawn entities from JSON
    // 4. UPDATE NextEntityId to max_loaded_id + 1 ← Prevents ID collision
    // 5. Set terrain_dirty flag
}
"save_scenario" => {
    // Responds with full scenario JSON via WS broadcast
    // Terrain grid + all entity data
}
```

> [!WARNING]
> **Entity ID Collision Prevention:** `load_scenario` MUST scan loaded entity IDs and set `NextEntityId = max(loaded_ids) + 1`. Otherwise, subsequent manual spawns produce duplicate IDs.

#### [MODIFY] [index.html](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/debug-visualizer/index.html)

```html
<section class="panel-section">
    <h2>Terrain Editor</h2>
    <div class="controls-row">
        <button id="paint-mode-btn" class="btn secondary">🖌 Paint Mode</button>
    </div>
    <div id="brush-tools" class="brush-toolbar" style="display: none;">
        <button class="brush-btn active" data-brush="wall">⬛ Wall</button>
        <button class="brush-btn" data-brush="mud">🟫 Mud</button>
        <button class="brush-btn" data-brush="pushable">🟧 Pushable</button>
        <button class="brush-btn" data-brush="clear">⬜ Clear</button>
    </div>
    <div class="controls-row" style="margin-top: 8px;">
        <button id="save-scenario-btn" class="btn secondary">💾 Save</button>
        <button id="load-scenario-btn" class="btn secondary">📂 Load</button>
        <input type="file" id="scenario-file-input" accept=".json" style="display:none">
    </div>
    <div class="controls-row">
        <button id="clear-terrain-btn" class="btn secondary">🗑 Clear All</button>
    </div>
</section>
```

#### [MODIFY] [visualizer.js](file:///Users/manifera/Documents/Study/mass-swarm-ai-simulator/debug-visualizer/visualizer.js)

Brush-to-cost mapping (UI-only, core never sees these names):
```js
const BRUSH_MAP = {
    wall:     { hard: 65535, soft: 0,   color: '#1a1a2e',  label: 'Wall' },
    mud:      { hard: 200,   soft: 30,  color: '#8b6914',  label: 'Mud' },
    pushable: { hard: 125,   soft: 50,  color: '#d4790e',  label: 'Pushable' },
    clear:    { hard: 100,   soft: 100, color: null,        label: 'Clear' },
};
```

Terrain rendering (on `#canvas-bg`):
```js
function drawTerrain(bgCtx) {
    // For each cell, if hard_cost != 100 or soft_cost != 100:
    //   Wall (65535): dark fill
    //   Mud (200): brown fill with alpha based on cost
    //   Pushable (125): orange fill
    // Clear cells are skipped (no draw)
}
```

---

## Feature 4: State Management

### SimState Gating

The simulation already has `SimState::Setup` and `SimState::Running`. Enforce proper gating:

| System | Runs in Setup? | Runs in Running? | Reason |
|--------|:-:|:-:|--------|
| `ws_command_system` | ✅ | ✅ | Must receive paint/spawn commands while paused |
| `ws_sync_system` | ✅ | ✅ | Must send terrain/entity data to visualizer |
| `flow_field_update_system` | ✅ | ✅ | Must recalc when terrain changes while paused |
| `visibility_update_system` | ✅ | ✅ | Must show fog while placing units |
| `movement_system` | ❌ | ✅ | Physics only when running |
| `interaction_system` | ❌ | ✅ | Combat only when running |
| `removal_system` | ❌ | ✅ | Death only when running |
| `wave_spawn_system` | ❌ | ✅ | Auto-spawn only when running |

### NextEntityId on Scenario Load

```rust
"load_scenario" => {
    // ... despawn all, apply terrain, spawn from JSON ...

    // CRITICAL: Prevent ID collision on subsequent manual spawns
    let max_id = loaded_entities.iter()
        .map(|e| e.id)
        .max()
        .unwrap_or(0);
    next_id.0 = max_id + 1;
}
```

---

## File Summary

### New Files
| File | Description |
|------|-------------|
| `micro-core/src/terrain.rs` | TerrainGrid resource — dual integer weights (hard_cost + soft_cost) |
| `micro-core/src/visibility.rs` | FactionVisibility resource — bit-packed, cell-deduplicated, wall-aware |
| `micro-core/src/systems/visibility.rs` | visibility_update_system |

### Modified Files
| File | Changes |
|------|---------|
| `micro-core/src/lib.rs` | Register `terrain` and `visibility` modules |
| `micro-core/src/main.rs` | Register TerrainGrid, FactionVisibility, VisionRadius; add visibility system; gate systems properly |
| `micro-core/src/components.rs` | Add `VisionRadius` component |
| `micro-core/src/pathfinding/flow_field.rs` | Add `cost_map: Option<&[u16]>` to `calculate()`, integer Dijkstra math |
| `micro-core/src/systems/flow_field_update.rs` | Pass terrain obstacles + hard_costs |
| `micro-core/src/systems/movement.rs` | Kinematic wall-sliding + soft_cost speed modifier |
| `micro-core/src/systems/ws_command.rs` | Fibonacci spiral spawn, `set_terrain`, `clear_terrain`, `load_scenario`, `save_scenario`; NextEntityId fix |
| `micro-core/src/systems/ws_sync.rs` | Add VisibilitySync @ 10 TPS |
| `micro-core/src/bridges/ws_protocol.rs` | VisibilitySync (bit-packed), TerrainSync message types |
| `micro-core/src/bridges/zmq_bridge/systems.rs` | FoW-filtered `build_state_snapshot()` — brain sees only visible enemies |
| `micro-core/src/bridges/zmq_protocol.rs` | Extended `StateSnapshot` with explored/visible/terrain fields |
| `debug-visualizer/index.html` | Spawn Tools, per-faction fog toggles, Terrain Editor panel, scenario save/load |
| `debug-visualizer/visualizer.js` | Spawn controls + ghost circle, fog renderer (bit-unpack), paint mode + drag, terrain renderer, scenario I/O |
| `debug-visualizer/style.css` | Brush toolbar, paint cursor, fog overlay, spawn ghost circle |

---

## Verification Plan

### Automated Tests
```bash
# Terrain
cargo test terrain::tests::default_costs_are_100
cargo test terrain::tests::wall_returns_max
cargo test terrain::tests::hard_obstacles_filters_walls
cargo test terrain::tests::oob_returns_wall

# Visibility
cargo test visibility::tests::bit_pack_set_get_roundtrip
cargo test visibility::tests::cell_deduplication_merges_5000_entities
cargo test visibility::tests::wall_blocks_vision

# Flow field
cargo test flow_field::tests::cost_map_none_unchanged    # backward compat
cargo test flow_field::tests::cost_map_200_doubles_chamfer
cargo test flow_field::tests::cost_map_max_acts_as_wall

# Spawn
cargo test ws_command::tests::fibonacci_spiral_no_overlap

# Integration
cargo test --no-default-features  # Production compiles without telemetry
```

### Browser Testing
1. **Mass Spawn:** Amount=500, spread=50 → Fibonacci spiral pattern, no overlap, no explosion
2. **Fog of War:** Toggle Swarm fog → black overlay, vision circles stop at walls
3. **Terrain Paint:** Draw wall line → flow field arrows route around → entities slide along walls
4. **Pushable:** Paint pushable zone → entities slow to 50%, flow field slightly avoids
5. **Scenario Save/Load:** Paint terrain + place units → Save → Reload page → Load → identical state
6. **Setup→Run:** Fresh open → paused → paint → place units → Play → simulation runs

