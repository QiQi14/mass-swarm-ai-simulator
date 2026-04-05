# Task 09 — Terrain Grid Resource

## Metadata
- **Task_ID:** task_09_terrain_grid
- **Execution_Phase:** Phase 1 (Parallel)
- **Model_Tier:** standard
- **Dependencies:** None
- **Context_Bindings:**
  - `.agents/skills/rust-code-standards/SKILL.md`
  - `implementation_plan.md` → Feature 3: Terrain Editor (Integer Dual-Weight)

## Target Files
- `micro-core/src/terrain.rs` — **NEW**
- `micro-core/src/lib.rs` — **MODIFY** (register module)

## Contract

The `TerrainGrid` resource uses an **Inverted Integer Cost Model** with dual weights:

```
hard_cost (u16): Dijkstra cost multiplier (scale 100)
  100 = normal path cost
  125 = 1.25× cost (pushable)
  200 = 2× cost (mud)
  u16::MAX = absolute wall (impassable)

soft_cost (u16): Movement speed percentage (0–100)
  100 = full speed
  50 = 50% speed (pushable)
  30 = 30% speed (mud)
  0 = stopped (but kinematic wall-sliding prevents permanent paralysis)
```

Grid dimensions match flow field: `ceil(world_size / cell_size)`.
Default `cell_size = 20.0` → `50×50 = 2,500 cells` for a 1000×1000 world.

## Strict Instructions

### 1. Create `micro-core/src/terrain.rs`

```rust
//! # Terrain Grid
//!
//! Paintable terrain weight grid affecting pathfinding and movement.
//! Contract-based — core sees only integers, never named terrain types.
//!
//! ## Ownership
//! - **Task:** task_09_terrain_grid
//! - **Contract:** implementation_plan.md → Feature 3: Terrain Editor
//!
//! ## Dual-Weight Model
//! - `hard_costs`: Dijkstra cost multiplier (scale 100).
//!   100 = normal, 200 = double cost, u16::MAX = impassable wall.
//! - `soft_costs`: Movement speed percentage (0–100).
//!   100 = full speed, 50 = half speed, 0 = stopped.

use bevy::prelude::*;
use serde::{Deserialize, Serialize};
```

Implement the `TerrainGrid` struct as a `Resource` with:
- Fields: `width: u32`, `height: u32`, `cell_size: f32`, `hard_costs: Vec<u16>`, `soft_costs: Vec<u16>`
- Derive: `Resource, Debug, Clone, Serialize, Deserialize`

Implement these methods:

1. `pub fn new(width: u32, height: u32, cell_size: f32) -> Self`
   - Initialize `hard_costs` and `soft_costs` to `vec![100u16; (width*height)]`

2. `pub fn get_hard_cost(&self, cell: IVec2) -> u16`
   - Out of bounds returns `u16::MAX` (wall)
   - In bounds returns `self.hard_costs[y * width + x]`

3. `pub fn get_soft_cost(&self, cell: IVec2) -> u16`
   - Out of bounds returns `0` (frozen)
   - In bounds returns `self.soft_costs[y * width + x]`

4. `pub fn set_cell(&mut self, x: u32, y: u32, hard: u16, soft: u16)`
   - Bounds-checked write to both arrays

5. `pub fn hard_obstacles(&self) -> Vec<IVec2>`
   - Returns all cells where `hard_cost == u16::MAX`

6. `fn in_bounds(&self, cell: IVec2) -> bool` (private helper)

7. `pub fn reset(&mut self)` — reset all costs to 100 (for `clear_terrain` command)

8. `pub fn world_to_cell(&self, x: f32, y: f32) -> IVec2`
   - Convert world coordinates to grid cell: `IVec2::new((x / cell_size).floor() as i32, (y / cell_size).floor() as i32)`

### 2. Register in `micro-core/src/lib.rs`

Add `pub mod terrain;` to the module declarations.

## Verification Strategy

**Test_Type:** unit
**Test_Stack:** `cargo test` (standard Rust)

**Mandated tests (in `terrain.rs`):**

1. `test_terrain_default_costs_are_100` — New grid has all hard=100, soft=100
2. `test_terrain_wall_returns_max` — `set_cell(2,2, u16::MAX, 0)` then `get_hard_cost(IVec2(2,2))` returns `u16::MAX`
3. `test_terrain_oob_returns_wall` — `get_hard_cost(IVec2(-1, 0))` returns `u16::MAX`
4. `test_terrain_oob_returns_frozen` — `get_soft_cost(IVec2(-1, 0))` returns `0`
5. `test_terrain_hard_obstacles_filters_walls` — Set 3 walls in a 5×5 grid → `hard_obstacles()` returns exactly those 3
6. `test_terrain_set_cell_bounds_check` — Setting out-of-bounds cell does nothing (no panic)
7. `test_terrain_reset_clears_all` — Set some cells, call `reset()`, verify all back to 100
8. `test_terrain_serialization_roundtrip` — serde JSON roundtrip preserves all data
9. `test_terrain_world_to_cell_conversion` — `world_to_cell(25.0, 45.0)` with `cell_size=20.0` returns `IVec2(1, 2)`

**Commands:**
```bash
cd micro-core && cargo test terrain
```
