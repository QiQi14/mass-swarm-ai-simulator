# Task 13 — WS Commands: Spawn, Terrain, Scenario

## Metadata
- **Task_ID:** task_13_ws_commands
- **Execution_Phase:** Phase 2 (depends on Task 09)
- **Model_Tier:** standard
- **Dependencies:**
  - Task 09 (`terrain.rs` — `TerrainGrid` resource)
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 1 (Mass Spawn) + Feature 3 (Terrain Commands) + Feature 4 (State Management)

## Target Files
- `micro-core/src/systems/ws_command.rs` — **MODIFY**

## Contract: Fibonacci Spiral + Terrain Commands + Scenario I/O

### spawn_wave Enhancement
Replace random scatter with Fibonacci Spiral. New params:
- `spread` (optional, default 0) — spiral radius in world units
- Skip wall cells during spawn

```rust
let golden_angle = 137.5f32.to_radians();
for i in 0..amount {
    let r = spread * (i as f32 / amount as f32).sqrt();
    let theta = i as f32 * golden_angle;
    let spawn_x = x + r * theta.cos();
    let spawn_y = y + r * theta.sin();
    // Skip wall cells
    if terrain.get_hard_cost(terrain.world_to_cell(spawn_x, spawn_y)) == u16::MAX { continue; }
    commands.spawn(( /* entity bundle + VisionRadius::default() */ ));
}
```

### New Commands

1. **`set_terrain`** — `{ cells: [{ x, y, hard, soft }, ...] }`
   - Batch update terrain cells
   - Mark terrain as "dirty" so flow field recalculates next tick

2. **`clear_terrain`** — no params
   - Call `terrain.reset()` (all hard=100, soft=100)
   - Mark dirty

3. **`save_scenario`** — no params
   - Build a JSON response with:
     - `terrain`: `{ hard_costs: [...], soft_costs: [...], width, height, cell_size }`
     - `entities`: `[{ id, x, y, faction_id, stats: [...] }]`
   - Broadcast via WS as `{ type: "scenario_data", ... }`

4. **`load_scenario`** — `{ terrain: { ... }, entities: [{ ... }] }`
   - Despawn ALL existing entities
   - Apply terrain data
   - Spawn entities from JSON
   - **CRITICAL:** Update `NextEntityId` to `max(loaded_entity_ids) + 1`
   - Mark terrain dirty

5. **`set_fog_faction`** — `{ faction_id: 0 }` or `{ faction_id: null }`
   - Set the `ActiveFogFaction` resource (created in Task 12)
   - When `null`/missing: disable fog streaming

## Strict Instructions

### 1. Modify `micro-core/src/systems/ws_command.rs`

**a. Add new resource imports:**
```rust
use crate::terrain::TerrainGrid;
use crate::components::VisionRadius;
```

**b. Add `terrain: ResMut<TerrainGrid>` to `ws_command_system` signature.**

**c. Refactor `spawn_wave` handler:**
- Read optional `spread` param (default 0.0)
- When `spread > 0`: use Fibonacci Spiral algorithm (see contract above)
- When `spread == 0`: spawn all at exact `(x, y)` (backward compatible)
- Add `VisionRadius::default()` to spawned entity bundles
- Skip wall cells: check `terrain.get_hard_cost()` before spawning

**d. Add `set_terrain` handler:**
- Parse `cells` array from params
- For each cell: `terrain.set_cell(x, y, hard, soft)`

**e. Add `clear_terrain` handler:**
- Call `terrain.reset()`

**f. Add `save_scenario` handler:**
- Build scenario JSON from terrain + all entities (via `faction_query`)
- Broadcast response as a WS message (use existing `sender`)

**g. Add `load_scenario` handler:**
- Despawn all entities (iterate `faction_query`, despawn each)
- Apply terrain: iterate cells, call `set_cell()`
- Spawn entities from JSON array (with EntityId, Position, Velocity, FactionId, StatBlock, VisionRadius)
- Update `next_id.0 = max_loaded_id + 1`

### 2. Entity Bundle on Spawn

All spawned entities (both `spawn_wave` and `load_scenario`) must include:
```rust
(
    EntityId { id: next_id.0 },
    Position { x: spawn_x, y: spawn_y },
    Velocity { dx: 0.0, dy: 0.0 },  // Start stationary for scenario load
    FactionId(faction_id),
    StatBlock::with_defaults(&stat_defaults),
    VisionRadius::default(),
)
```

## Verification Strategy

**Test_Type:** unit
**Test_Stack:** `cargo test` (standard Rust)

**Mandated tests (in `ws_command.rs`):**

1. `test_fibonacci_spiral_no_overlap` — Spawn 100 entities with spread=50, verify no two share coordinates within 0.1 units
2. `test_fibonacci_spiral_skips_walls` — Set wall at center, spawn → verify no entity spawned in wall cell
3. `test_set_terrain_updates_grid` — Send set_terrain command → verify terrain grid updated
4. `test_clear_terrain_resets_all` — Set terrain, then clear → verify all 100
5. `test_load_scenario_updates_next_entity_id` — Load 50 entities with IDs 1–50 → verify NextEntityId == 51

**Commands:**
```bash
cd micro-core && cargo test ws_command
```
