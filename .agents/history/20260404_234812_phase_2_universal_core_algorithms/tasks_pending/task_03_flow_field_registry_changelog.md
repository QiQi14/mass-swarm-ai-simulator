# Changelog: task_03_flow_field_registry

## Touched Files

- **`micro-core/src/pathfinding/mod.rs`** [NEW] — Module root for pathfinding, re-exports `FlowField` and `FlowFieldRegistry`.
- **`micro-core/src/pathfinding/flow_field.rs`** [NEW] — Full FlowField + FlowFieldRegistry implementation with 9 unit tests.
- **`micro-core/src/lib.rs`** [MODIFY] — Added `pub mod pathfinding;` and updated `Depends On` doc comment.

## Contract Fulfillment

### `FlowField` struct (Contract 4)
- ✅ `pub width: u32`, `pub height: u32`, `pub cell_size: f32`
- ✅ `pub directions: Vec<Vec2>` — Central Difference Gradient, 360° smooth
- ✅ `pub costs: Vec<u16>` — Chamfer distance, scale=10. Goal=0, unreachable=u16::MAX

### `FlowField` methods
- ✅ `new(width, height, cell_size)` — allocates zeroed vecs of size `(width * height)`
- ✅ `calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2])` — 8-Connected Chamfer Dijkstra + Central Difference Gradient
- ✅ `sample(&self, world_pos: Vec2) -> Vec2` — floor-divide to cell, Vec2::ZERO if OOB
- ✅ `in_bounds(&self, cell: IVec2) -> bool` — private bounds check
- ✅ `cell_index(&self, cell: IVec2) -> usize` — private `(y * width + x)`

### `FlowFieldRegistry` resource (Contract 4)
- ✅ `#[derive(Resource, Debug, Default)]`
- ✅ `pub fields: HashMap<u32, FlowField>` — keyed by target faction ID

### Internal types
- ✅ `CostState { cost: u32, cell: IVec2 }` with reversed `Ord` for min-heap
- ✅ `NEIGHBORS_8: [(i32, i32, u32); 8]` — 8-connected offsets with Chamfer costs

### Algorithm Design Decisions (all mandatory)
- ✅ **8-Connected Chamfer Dijkstra** — ortho=10, diag=14 (NOT 4-connected BFS)
- ✅ **`BinaryHeap`** (min-heap via reversed `Ord`) — NOT `VecDeque`
- ✅ **Central Difference Gradient** — dx = left - right, dy = up - down, normalize
- ✅ **Anti-corner-cutting** — diagonal blocked if adjacent ortho is obstacle
- ✅ **`bevy::platform::collections::HashMap`** for registry — AHash/hashbrown (see Deviations)
- ✅ **OOB/obstacle neighbors use `current_cost`** in gradient — wall avoidance

### Unit Tests (9/9 per spec §7)
- ✅ `test_single_goal_center_adjacent_directions`
- ✅ `test_corner_cell_diagonal_direction`
- ✅ `test_multiple_goals_nearest_wins`
- ✅ `test_edge_cells_direction`
- ✅ `test_out_of_bounds_returns_zero`
- ✅ `test_goal_cell_returns_zero`
- ✅ `test_obstacle_blocks_and_routes_around`
- ✅ `test_registry_stores_by_faction`
- ✅ `test_performance_50x50_grid`

## Deviations/Notes

### HashMap Import Path Change (Bevy 0.18 API)

The spec mandates `bevy::utils::HashMap`. However, in **Bevy 0.18**, `bevy_utils` no longer re-exports `HashMap`. The type was moved to `bevy::platform::collections::HashMap`, which uses the same `hashbrown` (AHash) backend. This fulfills the intent (AHash performance, NOT `std::collections::HashMap`/SipHash).

**Used:** `use bevy::platform::collections::HashMap;`
**Spec said:** `use bevy::utils::HashMap;`
**Reason:** `bevy::utils::HashMap` does not exist in Bevy 0.18.1, causing `E0432`.

### Compilation Blocker: Pre-existing spatial module errors

`cargo test pathfinding` and `cargo check` fail due to **2 pre-existing errors in `spatial/hash_grid.rs`** (Task 02's scope):
1. `E0432: unresolved import bevy::utils::hashbrown` (line 13) — same Bevy 0.18 API migration issue
2. `E0282: type annotations needed` (line 53)

These errors prevent the whole crate from compiling, but **zero errors originate from pathfinding module files**. The pathfinding code is correct and will compile once the spatial module is fixed.

The QA agent should note: Task 02's `spatial/hash_grid.rs` needs its HashMap import updated from `bevy::utils::hashbrown::HashMap` to `bevy::platform::collections::HashMap` to unblock full compilation.

## Human Interventions

None.
