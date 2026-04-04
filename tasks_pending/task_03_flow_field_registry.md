---
Task_ID: task_03_flow_field_registry
Execution_Phase: Phase 1 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/pathfinding/mod.rs
  - micro-core/src/pathfinding/flow_field.rs
  - micro-core/src/lib.rs
Dependencies:
  - task_01_context_agnostic_refactor
Context_Bindings:
  - context/conventions
  - context/architecture
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Implement a Dijkstra-based Vector Flow Field and a Flow Field Registry for N-faction pathfinding.

**Read `implementation_plan.md` Contract 4 for exact API.**

## 1. Create `micro-core/src/pathfinding/mod.rs` [NEW]

Re-export `flow_field::FlowField` and `flow_field::FlowFieldRegistry`.

## 2. Create `micro-core/src/pathfinding/flow_field.rs` [NEW]

### `FlowField` struct (NOT a Resource — owned by registry)

```rust
use bevy::prelude::*;
use std::collections::{HashMap, VecDeque};

#[derive(Debug)]
pub struct FlowField {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    pub directions: Vec<Vec2>,  // flat [y * width + x]
    pub costs: Vec<u16>,        // integration field
}
```

Implement:
- `new(width: u32, height: u32, cell_size: f32) -> Self` — allocate zeroed vecs of size `(width * height) as usize`.
- `calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2])`:
  1. Initialize all costs to `u16::MAX`.
  2. Convert each goal world-position to a cell coordinate. Set those cells' cost to 0 and push to a `VecDeque<IVec2>` (BFS queue).
  3. BFS flood-fill (4-connected: up/down/left/right):
     - Pop cell from queue.
     - For each neighbor: if not an obstacle and `current_cost + 1 < neighbor_cost`, update neighbor cost and push to queue.
  4. Direction pass: for each cell, examine all 4 neighbors. Find the neighbor with the lowest cost. Store the normalized direction vector from this cell toward that neighbor. If all neighbors are `u16::MAX`, store `Vec2::ZERO`.
- `sample(&self, world_pos: Vec2) -> Vec2`:
  - Convert world position to cell: `x = (world_pos.x / cell_size).floor() as i32`, same for y.
  - If cell is out of bounds (< 0 or >= width/height), return `Vec2::ZERO`.
  - Return `self.directions[(y * width + x) as usize]`.

### `FlowFieldRegistry` resource

```rust
#[derive(Resource, Debug, Default)]
pub struct FlowFieldRegistry {
    pub fields: HashMap<u32, FlowField>,
}
```

This stores one `FlowField` per target faction ID. The `flow_field_update_system` (Task 06) will populate this registry.

## 3. Update `micro-core/src/lib.rs` [MODIFY]

Add `pub mod pathfinding;` after existing module declarations.

## 4. Unit Tests

- **Single goal center:** 5×5 grid, goal at (2,2). Adjacent cells should have direction vectors pointing toward (2,2).
- **Multiple goals:** Two goals at opposite corners. Cells equidistant from both should point toward the nearer one.
- **Edge cells:** Goal at (0,0). Cells along the edge should have correct directions.
- **Out-of-bounds sample:** `sample()` at negative coordinates or beyond grid returns `Vec2::ZERO`.
- **Goal cell sample:** `sample()` at the goal position returns `Vec2::ZERO`.
- **Obstacles:** Place an obstacle cell. BFS should route around it.
- **Registry:** Insert two fields with different target faction IDs. Retrieve each by key.
- **Performance:** 50×50 grid with one goal — `calculate()` completes successfully (no panic).

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "Single goal produces correct directional vectors in adjacent cells"
  - "Multiple goals generate shortest-path field"
  - "sample() returns Vec2::ZERO for out-of-bounds positions"
  - "50x50 grid calculation completes successfully"
  - "FlowFieldRegistry stores/retrieves fields by target faction ID"
Suggested_Test_Commands:
  - "cd micro-core && cargo test pathfinding"
