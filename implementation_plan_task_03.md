# Task 03 — Flow Field + Registry (Full Specification)

> **Parent Plan:** [`implementation_plan.md`](./implementation_plan.md) → Contract 4
> **This file:** Exhaustive algorithmic spec for the Executor agent.

**Phase:** 1 (Parallel) | **Tier:** `standard` | **Domain:** Algorithm  
**Target Files:** `pathfinding/mod.rs` [NEW], `pathfinding/flow_field.rs` [NEW], `lib.rs` [MODIFY]  
**Dependencies:** None (standalone algorithm)  
**Context Bindings:** `context/conventions`, `context/architecture`, `skills/rust-code-standards`

---

## 1. The Three-Layer Algorithm

```
┌──────────────┐     ┌───────────────────────┐     ┌───────────────────────┐
│  Cost Field  │ ──→ │  Integration Field    │ ──→ │  Direction Field      │
│  (implicit)  │     │  (8-Connected Chamfer │     │  (Central Difference  │
│  all cells=1 │     │   Dijkstra via Heap)  │     │   Gradient, 360°)     │
│  obstacles=∞ │     │  u16 per cell         │     │  Vec2 per cell        │
└──────────────┘     └───────────────────────┘     └───────────────────────┘
```

**Phase 2 simplification:** The cost field is implicit — all cells cost 1 (×10 = 10 orthogonal, ×14 = 14 diagonal). Obstacles cost ∞ (`u16::MAX`).

---

## 2. Mathematical Foundation

### 2.1 Chamfer Distance (Integer L₂ Approximation)

Instead of true Euclidean distance (expensive `sqrt`), approximate using integer multipliers:

| Move Type | True Cost | Chamfer Cost |
|-----------|-----------|--------------|
| Orthogonal (←→↑↓) | 1.000 | **10** |
| Diagonal (↗↘↙↖) | 1.414 | **14** |

The wavefront expands as an **octagon** (closely approximating a circle), eliminating the Manhattan diamond artifact of 4-connected BFS.

**Why NOT 4-connected BFS:** The L₁ (Manhattan) norm creates diamond-shaped wavefronts. Entities moving diagonally exhibit rigid robotic staircases (UP→RIGHT→UP→RIGHT). At 10,000 entities, this creates visually catastrophic movement patterns.

**Why NOT Fast Marching Method (FMM):** Mathematically perfect (true L₂), but requires floating-point quadratic equation solving per cell — too expensive for real-time ECS loop.

### 2.2 Grid Coordinate System

```
grid_width  = ⌈world_width  / cell_size⌉   (as u32)
grid_height = ⌈world_height / cell_size⌉   (as u32)
index(x, y) = y * width + x   (flat 1D array, cache-friendly)
```

### 2.3 World-to-Cell Conversion

```
cell_x = ⌊world_x / cell_size⌋   (as i32)
cell_y = ⌊world_y / cell_size⌋   (as i32)
```

Out of bounds → return `Vec2::ZERO`.

### 2.4 Integration Field (Multi-Source Chamfer Dijkstra)

**Input:** Goal positions `G = {g₁, g₂, ..., gₘ}`, Obstacle cells `O`

```
1. INIT: costs[i] = u16::MAX  for all cells

2. For each goal gⱼ:
     cell = world_to_cell(gⱼ)
     if in_bounds(cell) AND cell ∉ O:
       costs[index(cell)] = 0
       heap.push(CostState { cost: 0, cell })

3. WHILE heap.pop() → { cost, cell }:
     if cost > costs[cell]:  continue  // stale entry

     for (dx, dy, move_cost) in NEIGHBORS_8:
       neighbor = cell + (dx, dy)
       if !in_bounds(neighbor) OR neighbor ∈ O:  continue

       // ANTI-CORNER-CUTTING: block diagonal through wall corners
       if move_cost == 14:  // diagonal move
         if (cell.x+dx, cell.y) ∈ O  OR  (cell.x, cell.y+dy) ∈ O:
           continue

       next_cost = cost + move_cost  // integer addition
       if next_cost < costs[neighbor]:
         costs[neighbor] = next_cost as u16
         heap.push(CostState { cost: next_cost, cell: neighbor })
```

**Multi-goal property:** Seeding ALL goals at cost 0 simultaneously makes Dijkstra naturally compute distance to the **nearest** goal for every cell.

### 2.5 Direction Field (Central Difference Gradient)

Instead of pointing to the lowest-cost neighbor (restricts to 8 discrete angles), compute the **mathematical downhill gradient** of the cost field:

```
For each cell (x, y):
  if costs[x,y] == u16::MAX OR costs[x,y] == 0:
    directions[x,y] = Vec2::ZERO
    continue

  // get_cost: returns neighbor cost, or current_cost if OOB/obstacle
  // This pushes vectors AWAY from walls (graceful wall avoidance)
  left  = get_cost(x-1, y)
  right = get_cost(x+1, y)
  up    = get_cost(x, y-1)
  down  = get_cost(x, y+1)

  // Central difference: water flows downhill (high → low cost)
  dx = (left as f32) - (right as f32)
  dy = (up as f32)   - (down as f32)

  directions[x,y] = normalize_or_zero(Vec2(dx, dy))
```

**Why NOT "point to lowest neighbor":** Restricts ALL vectors to exact 45°/90° angles (8 discrete directions). At 10K entities, creates visible banding. Central Difference produces smooth **360-degree analog vectors**.

---

## 3. Worked Example: 5×5 Grid, Goal at Center

Goal at world `(2.5, 2.5)`, `cell_size=1.0` → goal cell `(2,2)`.

**Integration Field (Chamfer costs, scale=10):**
```
  x→   0     1     2     3     4
y=0 [ 28 ][ 14 ][ 20 ][ 14 ][ 28 ]
y=1 [ 14 ][ 14 ][ 10 ][ 14 ][ 14 ]
y=2 [ 20 ][ 10 ][  0 ][ 10 ][ 20 ]   ← goal
y=3 [ 14 ][ 14 ][ 10 ][ 14 ][ 14 ]
y=4 [ 28 ][ 14 ][ 20 ][ 14 ][ 28 ]
```

Note the **octagonal** contours vs Manhattan diamonds.

**Direction Field — worked gradient for cell (0,0) (cost=28):**
- left = OOB → current_cost = 28
- right = cost(1,0) = 14
- up = OOB → current_cost = 28
- down = cost(0,1) = 14
- `dx = 28 - 14 = 14`, `dy = 28 - 14 = 14`
- `normalize(14, 14) = (0.707, 0.707)` → **smooth diagonal toward goal** ✓

---

## 4. Critical Design Decisions

### `bevy::utils::HashMap` (MANDATORY)

> Use `bevy::utils::HashMap` (AHash), NOT `std::collections::HashMap` (SipHash).
> AHash is ~3× faster for integer key lookups in game loops.

### Anti-Corner-Cutting (MANDATORY)

Diagonal moves through obstacles are blocked when either adjacent orthogonal cell is an obstacle:
```
Moving diag from (x,y) to (x+dx, y+dy):
  BLOCKED if obstacle_at(x+dx, y) OR obstacle_at(x, y+dy)
```
Prevents entities from visually phasing through wall corners.

---

## 5. Full Rust Implementation

### 5.1 `micro-core/src/pathfinding/mod.rs` [NEW]

```rust
//! # Pathfinding
//!
//! Dijkstra-based Vector Flow Fields for N-faction mass pathfinding.
//!
//! ## Ownership
//! - **Task:** task_03_flow_field_registry
//! - **Contract:** implementation_plan.md → Contract 4

pub mod flow_field;

pub use flow_field::{FlowField, FlowFieldRegistry};
```

### 5.2 `micro-core/src/pathfinding/flow_field.rs` [NEW]

```rust
//! # Flow Field
//!
//! Pre-computed vector flow field using 8-Connected Chamfer Dijkstra
//! and Central Difference Gradient for smooth 360° direction vectors.
//!
//! ## Ownership
//! - **Task:** task_03_flow_field_registry
//! - **Contract:** implementation_plan.md → Contract 4
//!
//! ## Algorithm
//! 1. Integration Field: Multi-source Chamfer Dijkstra (BinaryHeap)
//!    - Orthogonal cost: 10, Diagonal cost: 14
//!    - Anti-corner-cutting for diagonal obstacle traversal
//! 2. Direction Field: Central Difference Gradient
//!    - Produces smooth 360° analog vectors (not 8-way snapping)
//!    - OOB/obstacle neighbors use current_cost (wall avoidance)

use bevy::prelude::*;
use bevy::utils::HashMap;  // AHash — fast integer key lookups
use std::collections::{BinaryHeap, HashSet};
use std::cmp::Ordering;

/// Min-heap state for Dijkstra's algorithm.
///
/// `BinaryHeap` is a max-heap by default, so we reverse the
/// `Ord` implementation to get min-heap behavior.
#[derive(Copy, Clone, Eq, PartialEq)]
struct CostState {
    cost: u32,
    cell: IVec2,
}

impl Ord for CostState {
    fn cmp(&self, other: &Self) -> Ordering {
        // Reverse ordering for min-heap
        other.cost.cmp(&self.cost)
            .then_with(|| self.cell.x.cmp(&other.cell.x))
            .then_with(|| self.cell.y.cmp(&other.cell.y))
    }
}

impl PartialOrd for CostState {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

/// 8-connected neighbor offsets with Chamfer distance costs.
///
/// Orthogonal (cardinal) = 10 ≈ 1.0 × 10
/// Diagonal = 14 ≈ √2 × 10 ≈ 1.414 × 10
///
/// Integer arithmetic only — no floating-point in integration phase.
const NEIGHBORS_8: [(i32, i32, u32); 8] = [
    // Cardinal (cost 10)
    ( 0, -1, 10), ( 0,  1, 10), (-1,  0, 10), ( 1,  0, 10),
    // Diagonal (cost 14)
    (-1, -1, 14), ( 1, -1, 14), (-1,  1, 14), ( 1,  1, 14),
];

/// Pre-computed vector flow field for mass pathfinding.
///
/// Each cell stores a normalized direction vector pointing toward
/// the nearest goal. Entities sample their cell to get movement
/// direction. NOT a Resource — owned by `FlowFieldRegistry`.
///
/// ## Coordinate System
/// - Flat array indexed as `[y * width + x]`
/// - World-to-cell: `⌊world_pos / cell_size⌋`
/// - Cell `(0,0)` covers world area `[0, cell_size) × [0, cell_size)`
#[derive(Debug)]
pub struct FlowField {
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
    /// Direction vectors, indexed as `[y * width + x]`.
    /// Each vector is normalized (length 1.0) or `Vec2::ZERO`.
    /// Generated by Central Difference Gradient — smooth 360° angles.
    pub directions: Vec<Vec2>,
    /// Integration field costs (Chamfer distance to nearest goal).
    /// Scale: orthogonal=10, diagonal=14. Goal cells=0.
    /// `u16::MAX` = unreachable. True distance ≈ `cost / 10.0`.
    pub costs: Vec<u16>,
}

impl FlowField {
    /// Allocate a new flow field with zeroed vectors and costs.
    pub fn new(width: u32, height: u32, cell_size: f32) -> Self {
        let size = (width * height) as usize;
        Self {
            width,
            height,
            cell_size,
            directions: vec![Vec2::ZERO; size],
            costs: vec![0u16; size],
        }
    }

    /// Compute the flow field from goal positions, routing around obstacles.
    ///
    /// ## Phase 1: Integration Field (8-Connected Chamfer Dijkstra)
    /// - Seeds all goal cells at cost 0 in a `BinaryHeap` (min-heap).
    /// - Expands using Chamfer weights: ortho=10, diag=14.
    /// - Anti-corner-cutting: diag blocked if either adjacent ortho is obstacle.
    ///
    /// ## Phase 2: Direction Field (Central Difference Gradient)
    /// - For each cell, computes `dx = cost(left) - cost(right)`.
    /// - Produces smooth 360° vectors (not 8-way snapping).
    /// - OOB/obstacle neighbors use `current_cost` to push away from walls.
    pub fn calculate(&mut self, goals: &[Vec2], obstacles: &[IVec2]) {
        // ── Phase 1: Integration Field (Chamfer Dijkstra) ──
        self.costs.iter_mut().for_each(|c| *c = u16::MAX);

        let obstacle_set: HashSet<IVec2> = obstacles.iter().copied().collect();
        let mut heap = BinaryHeap::new();

        // Seed all goal cells at cost 0
        for &goal_world in goals {
            let gx = (goal_world.x / self.cell_size).floor() as i32;
            let gy = (goal_world.y / self.cell_size).floor() as i32;
            let cell = IVec2::new(gx, gy);

            if self.in_bounds(cell) && !obstacle_set.contains(&cell) {
                let idx = self.cell_index(cell);
                if self.costs[idx] != 0 {
                    self.costs[idx] = 0;
                    heap.push(CostState { cost: 0, cell });
                }
            }
        }

        // Dijkstra expansion with Chamfer weights
        while let Some(CostState { cost, cell }) = heap.pop() {
            let idx = self.cell_index(cell);
            // Skip stale entries (already found a shorter path)
            if cost > self.costs[idx] as u32 {
                continue;
            }

            for &(dx, dy, move_cost) in &NEIGHBORS_8 {
                let neighbor = IVec2::new(cell.x + dx, cell.y + dy);

                if !self.in_bounds(neighbor) || obstacle_set.contains(&neighbor) {
                    continue;
                }

                // Anti-corner-cutting: block diagonal if adjacent ortho is obstacle
                if move_cost == 14 {
                    let adj_x = IVec2::new(cell.x + dx, cell.y);
                    let adj_y = IVec2::new(cell.x, cell.y + dy);
                    if obstacle_set.contains(&adj_x) || obstacle_set.contains(&adj_y) {
                        continue;
                    }
                }

                let next_cost = cost.saturating_add(move_cost);
                let n_idx = self.cell_index(neighbor);

                if next_cost < self.costs[n_idx] as u32 {
                    self.costs[n_idx] = next_cost as u16;
                    heap.push(CostState { cost: next_cost, cell: neighbor });
                }
            }
        }

        // ── Phase 2: Direction Field (Central Difference Gradient) ──
        for y in 0..self.height as i32 {
            for x in 0..self.width as i32 {
                let cell = IVec2::new(x, y);
                let idx = self.cell_index(cell);
                let current_cost = self.costs[idx];

                if current_cost == u16::MAX || current_cost == 0 {
                    self.directions[idx] = Vec2::ZERO;
                    continue;
                }

                // get_cost: use current_cost for OOB/obstacle neighbors
                // This gracefully pushes vectors away from walls
                let get_cost = |nx: i32, ny: i32| -> u16 {
                    let n = IVec2::new(nx, ny);
                    if self.in_bounds(n) && !obstacle_set.contains(&n) {
                        self.costs[self.cell_index(n)]
                    } else {
                        current_cost
                    }
                };

                let left  = get_cost(x - 1, y) as f32;
                let right = get_cost(x + 1, y) as f32;
                let up    = get_cost(x, y - 1) as f32;
                let down  = get_cost(x, y + 1) as f32;

                // Water flows downhill: high cost → low cost
                let grad_x = left - right;
                let grad_y = up - down;

                self.directions[idx] = Vec2::new(grad_x, grad_y).normalize_or_zero();
            }
        }
    }

    /// Sample the flow field at a world position.
    ///
    /// Returns the direction vector for the cell containing `world_pos`.
    /// Returns `Vec2::ZERO` if position is out of grid bounds.
    pub fn sample(&self, world_pos: Vec2) -> Vec2 {
        let cx = (world_pos.x / self.cell_size).floor() as i32;
        let cy = (world_pos.y / self.cell_size).floor() as i32;

        if cx < 0 || cx >= self.width as i32 || cy < 0 || cy >= self.height as i32 {
            return Vec2::ZERO;
        }

        self.directions[(cy as u32 * self.width + cx as u32) as usize]
    }

    /// Check if a cell coordinate is within grid bounds.
    #[inline]
    fn in_bounds(&self, cell: IVec2) -> bool {
        cell.x >= 0 && cell.x < self.width as i32
            && cell.y >= 0 && cell.y < self.height as i32
    }

    /// Convert cell coordinate to flat array index.
    #[inline]
    fn cell_index(&self, cell: IVec2) -> usize {
        (cell.y as u32 * self.width + cell.x as u32) as usize
    }
}

/// Registry of flow fields, keyed by target faction ID.
///
/// Each field converges on entities of that faction.
/// Deduplication is automatic: multiple follower factions targeting
/// faction 1 share ONE flow field for faction 1.
#[derive(Resource, Debug, Default)]
pub struct FlowFieldRegistry {
    pub fields: HashMap<u32, FlowField>,
}
```

### 5.3 `micro-core/src/lib.rs` [MODIFY]

Add `pub mod pathfinding;` after existing module declarations.

---

## 6. Complexity Analysis

| Operation | Time | Space |
|-----------|------|-------|
| `new()` | O(W×H) | O(W×H) |
| `calculate()` — Dijkstra | O(W×H × log(W×H)) | O(W×H) heap |
| `calculate()` — Gradient | O(W×H × 4) | In-place |
| `sample()` | **O(1)** | None |
| **Total `calculate()`** | **O(W×H × log(W×H))** | O(W×H) |

50×50 grid = 2,500 cells → ~28K operations. Sub-millisecond in release Rust.

---

## 7. Unit Tests

```rust
// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_single_goal_center_adjacent_directions() {
        // 5×5 grid, cell_size=1.0, goal at (2.5, 2.5) → cell (2,2)
        let mut ff = FlowField::new(5, 5, 1.0);
        ff.calculate(&[Vec2::new(2.5, 2.5)], &[]);

        // Goal cell: cost=0, direction=ZERO
        assert_eq!(ff.costs[(2 * 5 + 2)], 0, "Goal cell cost must be 0");
        assert_eq!(ff.sample(Vec2::new(2.5, 2.5)), Vec2::ZERO, "Goal direction must be ZERO");

        // Cell (1,2): left of goal → positive x
        let dir = ff.sample(Vec2::new(1.5, 2.5));
        assert!(dir.x > 0.0, "Cell left of goal should point right, got {:?}", dir);

        // Cell (3,2): right of goal → negative x
        let dir = ff.sample(Vec2::new(3.5, 2.5));
        assert!(dir.x < 0.0, "Cell right of goal should point left, got {:?}", dir);

        // Cell (2,1): above goal → positive y
        let dir = ff.sample(Vec2::new(2.5, 1.5));
        assert!(dir.y > 0.0, "Cell above goal should point down, got {:?}", dir);

        // Cell (2,3): below goal → negative y
        let dir = ff.sample(Vec2::new(2.5, 3.5));
        assert!(dir.y < 0.0, "Cell below goal should point up, got {:?}", dir);
    }

    #[test]
    fn test_corner_cell_diagonal_direction() {
        let mut ff = FlowField::new(5, 5, 1.0);
        ff.calculate(&[Vec2::new(2.5, 2.5)], &[]);

        let dir = ff.sample(Vec2::new(0.5, 0.5));
        assert!(dir.x > 0.0 && dir.y > 0.0,
            "Corner should point diagonally toward goal, got {:?}", dir);

        // Verify ~45° (gradient produces smooth diagonal)
        let ratio = dir.x / dir.y;
        assert!((ratio - 1.0).abs() < 0.1, "Should be ~45°, ratio={}", ratio);
    }

    #[test]
    fn test_multiple_goals_nearest_wins() {
        let mut ff = FlowField::new(10, 1, 1.0);
        ff.calculate(&[Vec2::new(0.5, 0.5), Vec2::new(9.5, 0.5)], &[]);

        let dir3 = ff.sample(Vec2::new(3.5, 0.5));
        assert!(dir3.x < 0.0, "Cell 3 closer to goal 0, should point left");

        let dir7 = ff.sample(Vec2::new(7.5, 0.5));
        assert!(dir7.x > 0.0, "Cell 7 closer to goal 9, should point right");
    }

    #[test]
    fn test_edge_cells_direction() {
        let mut ff = FlowField::new(5, 5, 1.0);
        ff.calculate(&[Vec2::new(0.5, 0.5)], &[]);

        let dir = ff.sample(Vec2::new(4.5, 0.5));
        assert!(dir.x < 0.0, "Right edge should point left toward goal");
    }

    #[test]
    fn test_out_of_bounds_returns_zero() {
        let ff = FlowField::new(5, 5, 1.0);
        assert_eq!(ff.sample(Vec2::new(-1.0, 2.0)), Vec2::ZERO);
        assert_eq!(ff.sample(Vec2::new(2.0, -1.0)), Vec2::ZERO);
        assert_eq!(ff.sample(Vec2::new(5.0, 2.0)), Vec2::ZERO);
        assert_eq!(ff.sample(Vec2::new(2.0, 5.0)), Vec2::ZERO);
    }

    #[test]
    fn test_goal_cell_returns_zero() {
        let mut ff = FlowField::new(5, 5, 1.0);
        ff.calculate(&[Vec2::new(2.5, 2.5)], &[]);
        assert_eq!(ff.sample(Vec2::new(2.5, 2.5)), Vec2::ZERO, "Goal cell must be ZERO");
    }

    #[test]
    fn test_obstacle_blocks_and_routes_around() {
        let mut ff = FlowField::new(5, 3, 1.0);
        ff.calculate(&[Vec2::new(4.5, 1.5)], &[IVec2::new(2, 1)]);

        // Obstacle cell should have MAX cost
        assert_eq!(ff.costs[(1 * 5 + 2)], u16::MAX, "Obstacle must have MAX cost");

        // Cell (1,1) near obstacle should route around
        let dir = ff.sample(Vec2::new(1.5, 1.5));
        assert!(dir.x > 0.0 || dir.y.abs() > 0.01,
            "Should route around obstacle, got {:?}", dir);
    }

    #[test]
    fn test_registry_stores_by_faction() {
        let mut registry = FlowFieldRegistry::default();
        registry.fields.insert(0, FlowField::new(5, 5, 1.0));
        registry.fields.insert(1, FlowField::new(10, 10, 2.0));

        assert_eq!(registry.fields.len(), 2);
        assert_eq!(registry.fields.get(&0).unwrap().width, 5);
        assert_eq!(registry.fields.get(&1).unwrap().width, 10);
    }

    #[test]
    fn test_performance_50x50_grid() {
        let mut ff = FlowField::new(50, 50, 1.0);
        ff.calculate(&[Vec2::new(25.0, 25.0)], &[]);

        assert_eq!(ff.costs[(25 * 50 + 25)], 0, "Goal must be cost 0");
        assert!(ff.costs[0] > 0, "Corner should have positive cost");

        // Verify Chamfer distance at corner (0,0): ~25 diag × 14 = 350
        let corner = ff.costs[0];
        assert!(corner > 300 && corner < 400,
            "Corner Chamfer cost should be ~350, got {}", corner);
    }
}
```

---

## 8. Consumer Context: How Task 06 Uses This

The `flow_field_update_system` (Task 06) will:
1. Read `NavigationRuleSet` → unique target faction IDs.
2. For each target: query entities with `FactionId` → `Vec<Vec2>` goals.
3. `FlowField::new(grid_w, grid_h, config.flow_field_cell_size)`.
4. `field.calculate(&goals, &[])` (no obstacles in Phase 2).
5. Insert into `FlowFieldRegistry::fields`.

The `movement_system` (Task 06) **MUST** implement:
1. **Momentum smoothing:** `vel = vel.lerp(desired_vel, SMOOTHING_FACTOR)` — NOT direct velocity assignment.
2. **Boids separation:** Query `SpatialHashGrid` for same-faction neighbors, apply repulsion force to prevent "Swarm Crush" (infinite density singularity).

---

## 9. Verification Strategy

```yaml
Verification_Strategy:
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
```
