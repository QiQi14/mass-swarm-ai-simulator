# Algorithm Study: Chamfer Dijkstra Flow Fields for Mass Pathfinding

**Date:** 2026-04-04  
**Domain:** Pathfinding, Vector Fields, Game AI  
**Full Specification:** [implementation_plan_task_03.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_03.md)  
**Implementation:** [micro-core/src/pathfinding/flow_field.rs](../../micro-core/src/pathfinding/flow_field.rs)  
**Tags:** `dijkstra`, `flow-field`, `chamfer-distance`, `central-difference`, `pathfinding`

---

## 1. Problem Statement

10,000 entities need simultaneous pathfinding toward dynamic goals. Individual
A* per entity is O(N × V log V) where V = grid cells — computationally infeasible
at 2 TPS. A flow field computes ONE field that ALL entities share: O(V log V) total.

## 2. The Three-Layer Algorithm

```
┌──────────────┐     ┌────────────────────┐     ┌────────────────────┐
│  Cost Field  │ ──→ │  Integration Field  │ ──→ │  Direction Field   │
│  (implicit)  │     │  (8-Connected       │     │  (Central Diff     │
│  all cells=1 │     │   Chamfer Dijkstra) │     │   Gradient, 360°)  │
│  obstacles=∞ │     │  u16 per cell       │     │  Vec2 per cell     │
└──────────────┘     └────────────────────┘     └────────────────────┘
```

## 3. Layer 1: Chamfer Distance (Integer L₂ Approximation)

### Why Not 4-Connected BFS?

| Method | Distance Metric | Wavefront Shape | Visual Result |
|:---|:---|:---|:---|
| 4-connected BFS | L₁ (Manhattan) | Diamond | Robotic staircases |
| 8-connected Chamfer | L₂ approx (octagon) | Octagon ≈ circle | Smooth natural flow |
| Fast Marching (FMM) | True L₂ Euclidean | Perfect circle | Too expensive for ECS |

### Chamfer Weights

```
Orthogonal (←→↑↓): 10 ≈ 1.000 × 10
Diagonal (↗↘↙↖):   14 ≈ 1.414 × 10   (integer √2 × 10)
```

**Integer arithmetic only** — no floating-point in the integration phase. This is
critical for deterministic simulation across platforms.

### Multi-Source Dijkstra

Seeding ALL goals at cost 0 simultaneously makes Dijkstra compute distance to the
**nearest** goal for every cell. No per-entity pathfinding needed.

```
1. costs[*] = u16::MAX
2. For each goal: costs[goal_cell] = 0; heap.push(0, goal_cell)
3. While heap.pop() → (cost, cell):
     if cost > costs[cell]: continue   // stale
     for (dx, dy, move_cost) in NEIGHBORS_8:
       neighbor = cell + (dx, dy)
       if blocked: continue
       next_cost = cost + move_cost
       if next_cost < costs[neighbor]:
         costs[neighbor] = next_cost
         heap.push(next_cost, neighbor)
```

### Anti-Corner-Cutting

Diagonal moves through obstacles are blocked:
```
Moving from (x,y) to (x+dx, y+dy) diagonally:
  BLOCKED if obstacle_at(x+dx, y) OR obstacle_at(x, y+dy)
```
Prevents entities from visually phasing through wall corners.

## 4. Layer 2: Central Difference Gradient

### Why Not "Point to Lowest Neighbor"?

| Method | Precision | Visual Result |
|:---|:---|:---|
| Lowest neighbor | 8 discrete angles (45° steps) | Visible banding at 10K entities |
| Central Difference | Smooth 360° analog vectors | Natural organic flow |

### Algorithm

```
For each cell (x, y):
  left  = cost(x-1, y)   // OOB/obstacle → use current_cost
  right = cost(x+1, y)
  up    = cost(x, y-1)
  down  = cost(x, y+1)

  dx = left - right      // "water flows downhill"
  dy = up   - down

  direction = normalize(dx, dy)
```

**OOB/obstacle neighbors use `current_cost`** — this creates a repulsion effect
that flows around walls instead of into them.

## 5. Worked Example

5×5 grid, goal at center (2,2):

```
Integration Field (Chamfer costs, ×10 scale):
     0     1     2     3     4
0 [ 28 ][ 14 ][ 20 ][ 14 ][ 28 ]
1 [ 14 ][ 14 ][ 10 ][ 14 ][ 14 ]
2 [ 20 ][ 10 ][  0 ][ 10 ][ 20 ]  ← goal
3 [ 14 ][ 14 ][ 10 ][ 14 ][ 14 ]
4 [ 28 ][ 14 ][ 20 ][ 14 ][ 28 ]
```

Gradient at cell (0,0), cost=28:
- left = OOB → 28, right = cost(1,0) = 14
- up = OOB → 28, down = cost(0,1) = 14
- `dx = 28-14 = 14`, `dy = 28-14 = 14`
- `normalize(14, 14) = (0.707, 0.707)` → smooth diagonal ✓

## 6. Complexity

| Operation | Time | Space |
|:---|:---|:---|
| Integration (Dijkstra) | O(W×H × log(W×H)) | O(W×H) heap |
| Gradient | O(W×H × 4) | In-place |
| `sample()` | **O(1)** | None |
| **Total** | **O(W×H × log(W×H))** | O(W×H) |

50×50 grid = 2,500 cells → ~28K operations. Sub-millisecond in release Rust.

## 7. Terrain Cost Map Extension (Task 11)

Phase 2 added weighted costs: `next_cost = cost + (move_cost × terrain_hard[neighbor] / 100)`

This enables terrain types:
- `hard_cost = 100` → normal ground (baseline)
- `hard_cost = 200` → swamp (2× traverse cost)
- `hard_cost = u16::MAX` → wall (impassable)

## 8. Fog-of-War Integration (Study 004)

Flow fields must only use VISIBLE target entities as goals. If no targets are
visible, the flow field is removed → entities idle. See Study 004 for details.
