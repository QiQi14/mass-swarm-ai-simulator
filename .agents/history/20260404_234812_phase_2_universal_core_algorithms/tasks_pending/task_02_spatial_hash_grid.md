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

**Read `implementation_plan.md` Contract 3 AND the deep-dive spec `implementation_plan_task_02.md` for the exact API, full Rust implementation, math, edge cases, and unit tests.**

> **CRITICAL:** The spec file `implementation_plan_task_02.md` (project root) contains the COMPLETE Rust code. Copy the implementation from there — do NOT invent your own.

## Key Design Decisions (MANDATORY)

1. **`bevy::utils::HashMap`** — Use AHash (from Bevy), NOT `std::collections::HashMap` (SipHash). ~3× faster for integer keys.
2. **AABB radius query** — NOT fixed 9-cell. Compute bounding box in cell coords to support `radius > cell_size`.
3. **Squared distance filtering** — Use `dx*dx + dy*dy <= R*R` to avoid expensive `sqrt`.
4. **Full rebuild per tick** — Clear and reinsert all entities. Simpler and often faster than incremental for all-moving entities.

## File Structure

### 1. Create `micro-core/src/spatial/mod.rs` [NEW]

Re-export `hash_grid::SpatialHashGrid` and `hash_grid::update_spatial_grid_system`.

### 2. Create `micro-core/src/spatial/hash_grid.rs` [NEW]

Implement per the spec in `implementation_plan_task_02.md` §4.2:

- `SpatialHashGrid` resource using `bevy::utils::HashMap<IVec2, Vec<(Entity, Vec2)>>`
- `new(cell_size)` — panics if `cell_size <= 0.0`
- `rebuild(&mut self, entities)` — clear, reinsert, retain non-empty
- `query_radius(&self, center, radius)` — AABB cell range, squared distance check
- `for_each_in_radius(&self, center, radius, closure)` — Zero-allocation variant of `query_radius`. Executes closure for each entity found. Used by Task 06 movement to avoid 600K heap allocs/sec. See spec §4.2.
- `world_to_cell(&self, pos)` — `IVec2(floor(x/S), floor(y/S))`
- `update_spatial_grid_system` — Bevy system collecting `(Entity, &Position)` → `grid.rebuild()`

### 3. Update `micro-core/src/lib.rs` [MODIFY]

Add `pub mod spatial;` after existing module declarations.

## 4. Unit Tests

Copy the 8 unit tests from `implementation_plan_task_02.md` §6, plus:

- **Empty grid:** `query_radius` returns empty vec
- **Single entity found:** Insert one, query at position → found
- **Single entity not found:** Query far away → empty
- **Multi-cell query:** Entities in different cells, query spanning multiple cells
- **Exact cell boundary:** Entity at `(20.0, 20.0)` with `cell_size=20.0`
- **Radius filtering:** Only within-radius entities returned
- **Rebuild idempotent:** Double rebuild → no duplicates
- **Performance 1000:** 1000 entities rebuild + query succeeds
- **for_each_in_radius parity:** Same results as `query_radius` but via closure

---

# Verification_Strategy
Test_Type: unit
Test_Stack: cargo test
Acceptance_Criteria:
  - "query_radius returns correct entities within radius"
  - "query_radius excludes entities outside radius"
  - "rebuild correctly handles entities at cell boundaries"
  - "1000-entity rebuild completes successfully"
  - "Uses bevy::utils::HashMap (AHash), NOT std::collections::HashMap"
Suggested_Test_Commands:
  - "cd micro-core && cargo test spatial"
