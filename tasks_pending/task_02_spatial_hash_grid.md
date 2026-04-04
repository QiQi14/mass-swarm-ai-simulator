---
Task_ID: task_02_spatial_hash_grid
Execution_Phase: Phase 1 (Parallel)
Model_Tier: standard
Target_Files:
  - micro-core/src/spatial/mod.rs
  - micro-core/src/spatial/hash_grid.rs
  - micro-core/src/lib.rs
Dependencies:
  - task_01_context_agnostic_refactor
Context_Bindings:
  - context/conventions
  - context/architecture
  - skills/rust-code-standards
---

# STRICT INSTRUCTIONS

Implement a Spatial Hash Grid for O(1) proximity lookups. This is a pure data structure + system — no game logic.

**Read `implementation_plan.md` Contract 3 for the exact API.**

## 1. Create `micro-core/src/spatial/mod.rs` [NEW]

Re-export `hash_grid::SpatialHashGrid` and `hash_grid::update_spatial_grid_system`.

## 2. Create `micro-core/src/spatial/hash_grid.rs` [NEW]

```rust
use bevy::prelude::*;
use std::collections::HashMap;

#[derive(Resource, Debug)]
pub struct SpatialHashGrid {
    pub cell_size: f32,
    grid: HashMap<IVec2, Vec<(Entity, Vec2)>>,
}
```

Implement:
- `new(cell_size: f32) -> Self` — empty grid with given cell size.
- `rebuild(&mut self, entities: &[(Entity, Vec2)])` — clear all cells, reinsert all entities. For each entity, compute cell via `world_to_cell()`, push into that cell's vec.
- `query_radius(&self, center: Vec2, radius: f32) -> Vec<(Entity, Vec2)>` — compute the range of cells covered by a bounding box `[center - radius, center + radius]`. Iterate all cells in that range (NOT just 9-cell — use actual bounding box for large radii). For each entity in those cells, check Euclidean distance ≤ radius. Return matching entities.
- `world_to_cell(&self, pos: Vec2) -> IVec2` — `IVec2::new((pos.x / self.cell_size).floor() as i32, (pos.y / self.cell_size).floor() as i32)`.

Implement `update_spatial_grid_system`:
```rust
pub fn update_spatial_grid_system(
    mut grid: ResMut<SpatialHashGrid>,
    query: Query<(Entity, &Position)>,
) {
    let entities: Vec<(Entity, Vec2)> = query.iter()
        .map(|(e, p)| (e, Vec2::new(p.x, p.y)))
        .collect();
    grid.rebuild(&entities);
}
```

## 3. Update `micro-core/src/lib.rs` [MODIFY]

Add `pub mod spatial;` after existing module declarations.

## 4. Unit Tests

- **Empty grid:** `query_radius` on empty grid returns empty vec.
- **Single entity:** Insert one entity, query at its position returns it. Query at distant position returns empty.
- **Multi-cell:** Insert entities in different cells, query with radius spanning multiple cells returns correct subset.
- **Boundary exact:** Entity at exact cell boundary is found correctly.
- **Radius filtering:** Two entities at different distances from query center — only the one within radius is returned.
- **Rebuild idempotent:** Calling rebuild twice with same data produces same results.
- **Performance:** Rebuild with 1000 entities completes successfully (no panic/timeout).

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "query_radius returns correct entities within radius"
  - "query_radius excludes entities outside radius"
  - "rebuild correctly handles entities at cell boundaries"
  - "1000-entity rebuild completes successfully"
Suggested_Test_Commands:
  - "cd micro-core && cargo test spatial"
