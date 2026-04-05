# Algorithm Study: Spatial Hash Grid for O(1) Proximity Queries

**Date:** 2026-04-04  
**Domain:** Spatial Partitioning, Game Physics  
**Full Specification:** [implementation_plan_task_02.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_02.md)  
**Implementation:** [micro-core/src/spatial/hash_grid.rs](../../micro-core/src/spatial/hash_grid.rs)  
**Tags:** `spatial-indexing`, `hash-grid`, `proximity-query`, `zero-allocation`

---

## 1. Problem Statement

Naïve proximity queries are O(N²). At 10,000 entities ×60 TPS, that's **6 billion
comparisons per second**. We need O(K) queries where K is the number of nearby
entities, typically K ≪ N.

## 2. Algorithm: Sparse Hash Grid

### 2.1 Coordinate-to-Cell Mapping

```
cell_x = ⌊world_x / cell_size⌋
cell_y = ⌊world_y / cell_size⌋
cell_key = IVec2(cell_x, cell_y)
```

Using `floor()` (not truncation) correctly handles negative coordinates.

### 2.2 AABB Radius Query

For a query at center `(cx, cy)` with radius `R`, compute the **Axis-Aligned
Bounding Box** in cell coordinates:

```
min_cell = ⌊(center - R) / cell_size⌋
max_cell = ⌊(center + R) / cell_size⌋
```

Iterate ALL cells in the AABB range — NOT a fixed 3×3 neighborhood. This correctly
handles `R > cell_size`.

### 2.3 Squared Distance Filter

Avoid `sqrt()` — filter candidates with: `dx² + dy² ≤ R²`

## 3. Key Design Decisions

### 3.1 AHash vs SipHash

| Hash Function | Use Case | Speed |
|:---|:---|:---|
| `std::collections::HashMap` (SipHash) | DDoS-resistant, network inputs | Slow for game loops |
| `bevy::utils::HashMap` (AHash) | Integer keys, hot loops | **~3× faster** |

**Rule:** Always use `bevy::utils::HashMap` for spatial indices.

### 3.2 Full Rebuild vs Incremental Update

Full rebuild every tick is simpler and often faster than incremental because most
entities move. The `clear()` + reinsert pattern preserves allocated memory via
`Vec::clear()`, avoiding reallocation:

```rust
for bucket in self.grid.values_mut() {
    bucket.clear();  // Keeps allocated capacity
}
```

### 3.3 Zero-Allocation Closure Query

The `for_each_in_radius()` method avoids heap allocation entirely by using a
closure instead of returning a `Vec`:

```rust
grid.for_each_in_radius(center, radius, |entity, pos| {
    // Process each neighbor in-place — zero allocation
});
```

At 10K entities × 60 TPS = 600K proximity queries/sec. Avoiding allocation on each
one saves ~600K `Vec` allocs/sec.

### 3.4 Cell Size Selection

**Rule:** `cell_size ≈ max(interaction_range)`

Our system: `interaction_range = 15.0` → `cell_size = 20.0`. Most queries touch
3×3 = 9 cells. Larger cell sizes waste time scanning; smaller ones increase the
number of cells to check.

## 4. Complexity

| Operation | Time | Space |
|:---|:---|:---|
| `rebuild()` | O(N) | O(N) |
| `query_radius()` | O(K) where K = entities in searched cells | O(K) results |
| `for_each_in_radius()` | O(K) | **O(1)** — zero allocation |

## 5. Edge Cases Tested

| Case | Behavior |
|:---|:---|
| Empty grid | Returns empty ✓ |
| Entity at cell boundary (`pos=20.0, S=20.0`) | `floor(20.0/20.0)=1` → belongs to cell 1 ✓ |
| Entity at exact query center | `dist=0 ≤ R²` → included ✓ |
| Entity at exact radius boundary | `dist²==R²` → `≤` includes it ✓ |
| `rebuild()` called twice with same data | Idempotent (no duplicates) ✓ |
| 1000 entities | Performance test passes ✓ |
