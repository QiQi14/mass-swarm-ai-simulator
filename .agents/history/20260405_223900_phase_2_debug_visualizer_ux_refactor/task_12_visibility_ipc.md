# Task 12 — Visibility System + WS/ZMQ Integration

## Metadata
- **Task_ID:** task_12_visibility_ipc
- **Execution_Phase:** Phase 2 (depends on Task 09 + Task 10)
- **Model_Tier:** advanced
- **Dependencies:**
  - Task 09 (`terrain.rs` — `TerrainGrid` for wall-aware vision)
  - Task 10 (`visibility.rs` — `FactionVisibility`, `VisionRadius`)
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 2: Fog of War + Inter-Layer Architecture

## Target Files
- `micro-core/src/systems/visibility.rs` — **NEW**
- `micro-core/src/systems/mod.rs` — **MODIFY** (register module)
- `micro-core/src/systems/ws_sync.rs` — **MODIFY** (add VisibilitySync)
- `micro-core/src/bridges/ws_protocol.rs` — **MODIFY** (add VisibilitySync type)
- `micro-core/src/bridges/zmq_protocol.rs` — **MODIFY** (extend StateSnapshot)
- `micro-core/src/bridges/zmq_bridge/systems.rs` — **MODIFY** (FoW-filtered snapshot)

## Contract: Cell-Centric Deduplication + Wall-Aware Vision

### visibility_update_system Signature
```rust
pub fn visibility_update_system(
    mut visibility: ResMut<FactionVisibility>,
    terrain: Res<TerrainGrid>,
    query: Query<(&Position, &FactionId, &VisionRadius)>,
)
```

### Algorithm
1. Clear all `visible` grids (transient — rebuilt each tick)
2. Group entities into grid cells → `HashMap<(faction_id, cell_x, cell_y), max_vision_radius>`
   - This deduplicates: 5,000 entities in one cell = 1 vision calculation
3. For each unique occupied cell, flood-fill within vision radius:
   - Skip cells where `terrain.get_hard_cost(cell) == u16::MAX` (wall-aware, no X-ray)
   - Mark matching cells in both `visible` AND `explored` grids
   - Distance check: `dx² + dy² <= cell_radius²`

### VisibilitySync Protocol (WS)
```rust
#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisibilitySync {
    pub faction_id: u32,
    pub grid_width: u32,
    pub grid_height: u32,
    pub explored: Vec<u32>,  // Bit-packed
    pub visible: Vec<u32>,   // Bit-packed
}
```

Throttled to **10 TPS** (every 6th tick at 60 TPS). Only sends the faction currently selected by the debug visualizer (set via `set_fog_faction` WS command).

### ZMQ StateSnapshot Extension
```rust
pub struct StateSnapshot {
    // ... existing fields ...
    pub explored: Option<Vec<u32>>,     // Bit-packed explored grid
    pub visible: Option<Vec<u32>>,      // Bit-packed visible grid
    pub terrain_hard: Vec<u16>,
    pub terrain_soft: Vec<u16>,
    pub terrain_grid_w: u32,
    pub terrain_grid_h: u32,
    pub terrain_cell_size: f32,
}
```

### ZMQ FoW Filtering
`build_state_snapshot()` must filter entities:
- **Own faction entities**: always included (brain always sees its own units)
- **Enemy entities**: only if the entity's grid cell is in the brain's faction VISIBLE bit-grid
- This creates the ML information asymmetry

## Strict Instructions

### 1. Create `micro-core/src/systems/visibility.rs`

Implement `visibility_update_system` with:
- Step 1: Clear visible grids via `FactionVisibility::clear_all()`
- Step 2: Build `occupied: HashMap<(u32, i32, i32), f32>` from entity query
  - Key = (faction_id, cell_x, cell_y), Value = max vision radius in that cell
  - Use `bevy::platform::collections::HashMap` for consistency
- Step 3: For each occupied cell, iterate `[-cell_radius..=cell_radius]` in both axes
  - wall-aware: skip if `terrain.get_hard_cost(IVec2::new(nx, ny)) == u16::MAX`
  - distance check: `dx*dx + dy*dy <= cell_radius*cell_radius` (integer arithmetic)
  - Call `FactionVisibility::set_bit()` on both visible and explored grids
  - Call `ensure_faction()` before first access to a faction's grids

### 2. Register in `micro-core/src/systems/mod.rs`

Add `pub mod visibility;`

### 3. Modify `micro-core/src/bridges/ws_protocol.rs`

Add the `VisibilitySync` struct (cfg-gated under `debug-telemetry`).

### 4. Modify `micro-core/src/systems/ws_sync.rs`

- Add a new resource `ActiveFogFaction(Option<u32>)` (defines which faction's fog to stream)
- Add `visibility: Res<FactionVisibility>` to the system signature
- Add `fog_faction: Res<ActiveFogFaction>` to the system signature
- Every 6th tick (when `tick.tick % 6 == 0`), populate `VisibilitySync` for the active faction
- Add the `set_fog_faction` command handler in `ws_command.rs` to set this resource

### 5. Modify `micro-core/src/bridges/zmq_protocol.rs`

Add the new fields to `StateSnapshot` (all `Option` for backward compat):
- `explored`, `visible`, terrain fields

### 6. Modify `micro-core/src/bridges/zmq_bridge/systems.rs`

Refactor `build_state_snapshot()`:
- Add `visibility: &FactionVisibility`, `terrain: &TerrainGrid`, `brain_faction: u32` parameters
- Filter entity iteration: own faction always included, enemies only if in visible cell
- Include explored/visible bit-packed grids and terrain data in snapshot
- Add `visibility: Res<FactionVisibility>` and `terrain: Res<TerrainGrid>` to `ai_trigger_system` args

## Verification Strategy

**Test_Type:** unit
**Test_Stack:** `cargo test` (standard Rust)

**Mandated tests:**

In `systems/visibility.rs`:
1. `test_visibility_clears_visible_each_tick` — entity moves away, previous cell no longer visible
2. `test_visibility_wall_blocks_vision` — entity behind wall cell is NOT visible
3. `test_visibility_explored_persists` — entity visits cell, moves away → cell still explored
4. `test_visibility_cell_deduplication` — 100 entities in same cell → same result as 1 entity (performance)
5. `test_visibility_multi_faction_independent` — faction 0 vision doesn't affect faction 1

In `bridges/zmq_bridge/systems.rs`:
6. `test_snapshot_filters_enemies_by_fog` — enemy in fog NOT in snapshot, enemy in visible IS in snapshot
7. `test_snapshot_always_includes_own_entities` — own faction entities always present regardless of fog

**Commands:**
```bash
cd micro-core && cargo test visibility
cd micro-core && cargo test zmq
```
