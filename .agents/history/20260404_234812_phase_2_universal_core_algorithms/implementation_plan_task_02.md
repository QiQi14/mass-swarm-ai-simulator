# Task 02 — Spatial Hash Grid (Full Specification)

> **Parent Plan:** [`implementation_plan.md`](./implementation_plan.md) → Contract 3
> **This file:** Exhaustive algorithmic spec for the Executor agent.

**Phase:** 1 (Parallel) | **Tier:** `standard` | **Domain:** Data Structure  
**Target Files:** `spatial/mod.rs` [NEW], `spatial/hash_grid.rs` [NEW], `lib.rs` [MODIFY]  
**Dependencies:** Task 01 (`Position` component — structurally unchanged)  
**Context Bindings:** `context/conventions`, `context/architecture`, `skills/rust-code-standards`

---

## 1. Concept: Why a Spatial Hash Grid?

Naïve proximity queries are **O(N²)** — every entity checks every other entity. At 10,000 entities, that's 100M comparisons per tick. A spatial hash grid partitions continuous 2D space into discrete cells, reducing proximity queries to **O(K)** where K is the number of entities in nearby cells.

## 2. Mathematical Foundation

### 2.1 Coordinate-to-Cell Mapping

Given an entity at world position `(wx, wy)` and a cell size `S`:

```
cell_x = ⌊wx / S⌋
cell_y = ⌊wy / S⌋
cell_key = IVec2(cell_x, cell_y)
```

### 2.2 Radius Query: AABB Cell Range

For a query at center `(cx, cy)` with radius `R`:

```
min_cell_x = ⌊(cx - R) / S⌋
max_cell_x = ⌊(cx + R) / S⌋
min_cell_y = ⌊(cy - R) / S⌋
max_cell_y = ⌊(cy + R) / S⌋
```

Iterate ALL cells in `[min_cell_x..=max_cell_x] × [min_cell_y..=max_cell_y]` (not just fixed 9-cell). This correctly handles `R > S`.

### 2.3 Distance Filtering (Squared Euclidean)

For each candidate entity `(ex, ey)`, verify using **squared distance** (avoids `sqrt`):

```
dx = ex - cx;  dy = ey - cy
included = (dx² + dy²) ≤ R²
```

### 2.4 Cell Size Selection

**Rule:** `cell_size ≈ max(interaction_range)`. Swarm demo: `InteractionRule.range = 15.0` → `cell_size = 20.0`. Most queries touch 3×3 cells.

---

## 3. Critical Design Decision: `bevy::utils::HashMap`

> **MANDATORY:** Use `bevy::utils::HashMap` (AHash), NOT `std::collections::HashMap` (SipHash).
>
> `std::collections::HashMap` uses SipHash (DDoS-resistant, slow for game loops).
> `bevy::utils::HashMap` uses AHash — optimized for fast integer key lookups. ~3× faster.

---

## 4. Full Rust Implementation

### 4.1 `micro-core/src/spatial/mod.rs` [NEW]

```rust
//! # Spatial Partitioning
//!
//! Hash grid for O(1) amortized proximity lookups.
//!
//! ## Ownership
//! - **Task:** task_02_spatial_hash_grid
//! - **Contract:** implementation_plan.md → Contract 3

pub mod hash_grid;

pub use hash_grid::{SpatialHashGrid, update_spatial_grid_system};
```

### 4.2 `micro-core/src/spatial/hash_grid.rs` [NEW]

```rust
//! # Spatial Hash Grid
//!
//! Sparse hash grid for proximity queries. Rebuilt every tick.
//!
//! ## Ownership
//! - **Task:** task_02_spatial_hash_grid
//! - **Contract:** implementation_plan.md → Contract 3
//!
//! ## Depends On
//! - `crate::components::Position`

use bevy::prelude::*;
use bevy::utils::HashMap;  // AHash — 3× faster than std SipHash
use crate::components::Position;

/// Spatial hash grid for O(1) amortized proximity lookups.
///
/// The grid is rebuilt every tick by `update_spatial_grid_system`.
/// Entities are bucketed into cells via floor-division of their
/// world position by `cell_size`. Uses `bevy::utils::HashMap`
/// (AHash) for fast integer key lookups.
///
/// ## Performance
/// - `rebuild()`: O(N) where N = entity count
/// - `query_radius()`: O(K) where K = entities in searched cells
/// - Memory: O(N) — only occupied cells stored (sparse)
#[derive(Resource, Debug)]
pub struct SpatialHashGrid {
    pub cell_size: f32,
    grid: HashMap<IVec2, Vec<(Entity, Vec2)>>,
}

impl SpatialHashGrid {
    /// Creates an empty grid with the given cell size.
    ///
    /// # Panics
    /// Panics if `cell_size <= 0.0`.
    pub fn new(cell_size: f32) -> Self {
        assert!(cell_size > 0.0, "cell_size must be positive");
        Self {
            cell_size,
            grid: HashMap::default(),
        }
    }

    /// Clears all cells and reinserts all entities.
    ///
    /// Called once per tick. Full rebuild is simpler and often faster
    /// than incremental updates because most entities move every tick.
    pub fn rebuild(&mut self, entities: &[(Entity, Vec2)]) {
        // Clear existing entries but keep allocated memory
        for bucket in self.grid.values_mut() {
            bucket.clear();
        }
        // Reinsert all entities
        for &(entity, pos) in entities {
            let cell = self.world_to_cell(pos);
            self.grid.entry(cell).or_default().push((entity, pos));
        }
        // Remove empty buckets to prevent unbounded memory growth
        self.grid.retain(|_, v| !v.is_empty());
    }

    /// Returns all entities within `radius` of `center`.
    ///
    /// ## Algorithm
    /// 1. Compute AABB of query circle in cell coordinates.
    /// 2. Iterate all cells in the AABB range.
    /// 3. For each entity, check squared Euclidean distance ≤ R².
    pub fn query_radius(&self, center: Vec2, radius: f32) -> Vec<(Entity, Vec2)> {
        let mut results = Vec::new();
        let radius_sq = radius * radius;

        // AABB in cell coordinates
        let min_cell = self.world_to_cell(center - Vec2::splat(radius));
        let max_cell = self.world_to_cell(center + Vec2::splat(radius));

        for cy in min_cell.y..=max_cell.y {
            for cx in min_cell.x..=max_cell.x {
                if let Some(bucket) = self.grid.get(&IVec2::new(cx, cy)) {
                    for &(entity, pos) in bucket {
                        let diff = pos - center;
                        if diff.x * diff.x + diff.y * diff.y <= radius_sq {
                            results.push((entity, pos));
                        }
                    }
                }
            }
        }
        results
    }

    /// Zero-allocation radius query. Executes closure `f` for each entity found.
    ///
    /// Unlike `query_radius()`, this allocates nothing — the closure processes
    /// each entity in-place. Used by the movement system (Task 06) for 10K+
    /// entity separation queries at 60 TPS, avoiding 600K heap allocs/sec.
    ///
    /// ## Algorithm
    /// Same AABB cell scan + squared distance filter as `query_radius()`.
    pub fn for_each_in_radius<F>(&self, center: Vec2, radius: f32, mut f: F)
    where
        F: FnMut(Entity, Vec2),
    {
        let radius_sq = radius * radius;
        let min_cell = self.world_to_cell(center - Vec2::splat(radius));
        let max_cell = self.world_to_cell(center + Vec2::splat(radius));

        for cy in min_cell.y..=max_cell.y {
            for cx in min_cell.x..=max_cell.x {
                if let Some(bucket) = self.grid.get(&IVec2::new(cx, cy)) {
                    for &(entity, pos) in bucket {
                        let diff = pos - center;
                        if diff.x * diff.x + diff.y * diff.y <= radius_sq {
                            f(entity, pos);
                        }
                    }
                }
            }
        }
    }

    /// Converts world position to cell coordinate via floor division.
    ///
    /// Math: `cell = IVec2(⌊wx/S⌋, ⌊wy/S⌋)`
    /// Handles negative coordinates correctly (floor, not truncation).
    fn world_to_cell(&self, pos: Vec2) -> IVec2 {
        IVec2::new(
            (pos.x / self.cell_size).floor() as i32,
            (pos.y / self.cell_size).floor() as i32,
        )
    }
}

/// Rebuilds the spatial hash grid every tick from all entity positions.
///
/// Runs in `Update` schedule, before `interaction_system`.
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

### 4.3 `micro-core/src/lib.rs` [MODIFY]

Add `pub mod spatial;` after existing module declarations.

---

## 5. Edge Case Handling

| Edge Case | Expected Behavior | How Handled |
|-----------|-------------------|-------------|
| Empty grid | `query_radius` → empty `Vec` | AABB loop finds no cells |
| Entity at cell boundary (pos=20.0, S=20.0) | Belongs to cell `(1,_)` | `floor(20.0/20.0) = 1` ✓ |
| Negative coordinates | Correct cell via `floor()` | `floor(-0.5/20.0) = -1` ✓ |
| Radius > cell_size | Covers >9 cells | AABB range auto-expands |
| Entity at exact query center | dist=0 ≤ R² | Included ✓ |
| Entity at exact radius boundary | dist²==R² | `<=` includes it ✓ |
| Double `rebuild()` same data | Idempotent | `.clear()` before reinsert |

---

## 6. Unit Tests

```rust
// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::ecs::world::World;

    fn make_entity(world: &mut World) -> Entity {
        world.spawn_empty().id()
    }

    #[test]
    fn test_query_radius_empty_grid_returns_empty() {
        let grid = SpatialHashGrid::new(20.0);
        let results = grid.query_radius(Vec2::new(50.0, 50.0), 10.0);
        assert!(results.is_empty(), "Empty grid should return no results");
    }

    #[test]
    fn test_single_entity_found_at_position() {
        let mut world = World::new();
        let e = make_entity(&mut world);
        let mut grid = SpatialHashGrid::new(20.0);
        grid.rebuild(&[(e, Vec2::new(50.0, 50.0))]);

        let results = grid.query_radius(Vec2::new(50.0, 50.0), 5.0);
        assert_eq!(results.len(), 1, "Should find entity at exact position");
        assert_eq!(results[0].0, e);
    }

    #[test]
    fn test_single_entity_not_found_when_distant() {
        let mut world = World::new();
        let e = make_entity(&mut world);
        let mut grid = SpatialHashGrid::new(20.0);
        grid.rebuild(&[(e, Vec2::new(50.0, 50.0))]);

        let results = grid.query_radius(Vec2::new(200.0, 200.0), 5.0);
        assert!(results.is_empty(), "Distant query should find nothing");
    }

    #[test]
    fn test_multi_cell_radius_query() {
        let mut world = World::new();
        let e1 = make_entity(&mut world);
        let e2 = make_entity(&mut world);
        let e3 = make_entity(&mut world);
        let mut grid = SpatialHashGrid::new(20.0);
        grid.rebuild(&[
            (e1, Vec2::new(10.0, 10.0)),
            (e2, Vec2::new(30.0, 10.0)),
            (e3, Vec2::new(90.0, 90.0)),
        ]);

        let results = grid.query_radius(Vec2::new(20.0, 10.0), 15.0);
        assert_eq!(results.len(), 2, "Should find e1 and e2, not e3");
    }

    #[test]
    fn test_exact_cell_boundary_entity() {
        let mut world = World::new();
        let e = make_entity(&mut world);
        let mut grid = SpatialHashGrid::new(20.0);
        grid.rebuild(&[(e, Vec2::new(20.0, 20.0))]);

        let results = grid.query_radius(Vec2::new(20.0, 20.0), 1.0);
        assert_eq!(results.len(), 1, "Boundary entity must be found");
    }

    #[test]
    fn test_radius_filtering_excludes_outside() {
        let mut world = World::new();
        let e_near = make_entity(&mut world);
        let e_far = make_entity(&mut world);
        let mut grid = SpatialHashGrid::new(20.0);
        grid.rebuild(&[
            (e_near, Vec2::new(5.0, 0.0)),
            (e_far, Vec2::new(15.0, 0.0)),
        ]);

        let results = grid.query_radius(Vec2::ZERO, 10.0);
        assert_eq!(results.len(), 1, "Only e_near (dist=5) within R=10");
        assert_eq!(results[0].0, e_near);
    }

    #[test]
    fn test_rebuild_idempotent() {
        let mut world = World::new();
        let e = make_entity(&mut world);
        let mut grid = SpatialHashGrid::new(20.0);
        let data = vec![(e, Vec2::new(50.0, 50.0))];
        grid.rebuild(&data);
        grid.rebuild(&data);

        let results = grid.query_radius(Vec2::new(50.0, 50.0), 5.0);
        assert_eq!(results.len(), 1, "Double rebuild must not duplicate");
    }

    #[test]
    fn test_performance_1000_entities() {
        let mut world = World::new();
        let entities: Vec<(Entity, Vec2)> = (0..1000)
            .map(|i| {
                let e = make_entity(&mut world);
                let pos = Vec2::new((i % 50) as f32 * 20.0, (i / 50) as f32 * 20.0);
                (e, pos)
            })
            .collect();

        let mut grid = SpatialHashGrid::new(20.0);
        grid.rebuild(&entities);
        let results = grid.query_radius(Vec2::new(500.0, 200.0), 50.0);
        assert!(!results.is_empty(), "Should find some entities near center");
    }
}
```

---

## 7. Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "query_radius returns correct entities within radius"
    - "query_radius excludes entities outside radius"
    - "rebuild correctly handles entities at cell boundaries"
    - "1000-entity rebuild completes successfully"
    - "Uses bevy::utils::HashMap (AHash), not std HashMap"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test spatial"
```
