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

**Read `implementation_plan.md` Contract 4 AND the deep-dive spec `implementation_plan_task_03.md` for the exact algorithm, full Rust implementation, worked examples, and unit tests.**

> **CRITICAL:** The spec file `implementation_plan_task_03.md` (project root) contains the COMPLETE Rust code. Copy the implementation from there — do NOT invent your own algorithm. The algorithm has been mathematically reviewed and architecture-approved.

## Key Design Decisions (MANDATORY — DO NOT DEVIATE)

1. **8-Connected Chamfer Dijkstra** — NOT 4-connected BFS. Orthogonal cost = 10, diagonal cost = 14. This produces octagonal wavefronts (approximating circles) instead of Manhattan diamond artifacts.
2. **`BinaryHeap`** (min-heap via reversed `Ord`) — NOT `VecDeque` (BFS). Required for weighted edge traversal.
3. **Central Difference Gradient** for direction vectors — NOT "point to lowest-cost neighbor". Computes `dx = cost(left) - cost(right)`, `dy = cost(up) - cost(down)` then normalizes. Produces smooth 360° analog vectors.
4. **Anti-corner-cutting** — Diagonal moves through obstacles are blocked when either adjacent orthogonal cell is an obstacle.
5. **`bevy::utils::HashMap`** for `FlowFieldRegistry` — AHash performance, NOT `std::collections::HashMap`.
6. **OOB/obstacle neighbors use `current_cost`** in gradient computation — this pushes direction vectors away from walls.

## File Structure

### 1. Create `micro-core/src/pathfinding/mod.rs` [NEW]

Re-export `flow_field::FlowField` and `flow_field::FlowFieldRegistry`.

### 2. Create `micro-core/src/pathfinding/flow_field.rs` [NEW]

Implement per the spec in `implementation_plan_task_03.md` §5.2. The file must contain:

**Internal types:**
- `CostState` — `{ cost: u32, cell: IVec2 }` with reversed `Ord` for min-heap
- `NEIGHBORS_8` — 8-connected offsets with Chamfer costs: `[(i32, i32, u32); 8]`

**`FlowField` struct (NOT a Resource — owned by registry):**
```rust
pub struct FlowField {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    pub directions: Vec<Vec2>,  // Central Difference Gradient — 360° smooth
    pub costs: Vec<u16>,        // Chamfer distance, scale=10. Goal=0, unreachable=u16::MAX
}
```

**Methods:**
- `new(width, height, cell_size)` — allocate zeroed vecs of size `(width * height)`
- `calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2])`:
  1. **Phase 1 — Integration Field (Chamfer Dijkstra):**
     - Reset all costs to `u16::MAX`
     - Convert each goal world-position to cell. Set cost=0, push to `BinaryHeap`
     - While heap not empty: pop `CostState`, skip if stale (`cost > costs[cell]`)
     - For each of 8 neighbors: skip OOB, skip obstacles, **skip diagonal if adjacent ortho is obstacle** (anti-corner-cutting)
     - `next_cost = cost + move_cost` (10 or 14). If `next_cost < neighbor cost`, update and push
  2. **Phase 2 — Direction Field (Central Difference Gradient):**
     - For each cell: if unreachable or goal → `Vec2::ZERO`
     - `get_cost(nx, ny)` → returns neighbor cost, or `current_cost` if OOB/obstacle
     - `dx = left - right`, `dy = up - down` (as f32)
     - `directions[idx] = Vec2::new(dx, dy).normalize_or_zero()`
- `sample(&self, world_pos: Vec2)` — floor-divide to cell, return direction or `Vec2::ZERO` if OOB
- `in_bounds(&self, cell: IVec2) -> bool` — bounds check (private)
- `cell_index(&self, cell: IVec2) -> usize` — `(y * width + x)` (private)

**`FlowFieldRegistry` resource:**
```rust
#[derive(Resource, Debug, Default)]
pub struct FlowFieldRegistry {
    pub fields: HashMap<u32, FlowField>,  // bevy::utils::HashMap
}
```

### 3. Update `micro-core/src/lib.rs` [MODIFY]

Add `pub mod pathfinding;` after existing module declarations.

## 4. Unit Tests

Copy the 9 unit tests from `implementation_plan_task_03.md` §7:

- **Single goal center:** 5×5 grid, goal at (2,2). Adjacent cells point toward goal. Goal cell = `Vec2::ZERO`.
- **Corner diagonal:** Cell (0,0) with goal at center → smooth ~45° diagonal direction.
- **Multiple goals:** Two goals at opposite ends. Cells point toward nearest (Chamfer distance).
- **Edge cells:** Goal at (0,0). Right edge cell points left.
- **Out-of-bounds:** `sample()` at negative/beyond returns `Vec2::ZERO`.
- **Goal cell:** `sample()` at goal position returns `Vec2::ZERO`.
- **Obstacles:** Place obstacle. BFS routes around. Anti-corner-cutting prevents phasing through.
- **Registry:** Insert two fields with different faction IDs. Retrieve each by key.
- **Performance 50×50:** `calculate()` completes successfully. Corner Chamfer cost ~350.

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "Single goal produces gradient directions (360° smooth, not 8-way snap)"
  - "Corner cells have diagonal gradient ~45°"
  - "Multiple goals direct to nearest (Chamfer distance)"
  - "sample() returns Vec2::ZERO for out-of-bounds and goal cells"
  - "Obstacles route flow around (anti-corner-cutting)"
  - "50×50 grid calculate completes < 5ms"
  - "FlowFieldRegistry stores/retrieves by target faction ID"
  - "Uses BinaryHeap (Dijkstra), NOT VecDeque (BFS)"
  - "Uses bevy::utils::HashMap, NOT std::collections::HashMap"
Suggested_Test_Commands:
  - "cd micro-core && cargo test pathfinding"
