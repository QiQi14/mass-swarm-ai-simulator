# Architecture Study: Bit-Packed Fog of War with Per-Faction Visibility

**Date:** 2026-04-04  
**Domain:** Game Systems, Fog of War, Data Compression  
**Full Specification:** [implementation_plan (Phase 2)](../../.agents/history/20260405_223900_phase_2_debug_visualizer_ux_refactor/implementation_plan.md)  
**Implementation:** [micro-core/src/visibility.rs](../../micro-core/src/visibility.rs), [micro-core/src/systems/visibility.rs](../../micro-core/src/systems/visibility.rs)  
**Tags:** `fog-of-war`, `bit-packing`, `information-asymmetry`, `ml-training`

---

## 1. Problem Statement

Each faction needs independent "fog of war" — a grid tracking which cells each
faction can currently see and which it has ever explored. At 50×50 grid × N factions,
naïve `bool` arrays waste 97% of bits. We need compact storage that efficiently
serializes over WebSocket and ZMQ for the debug visualizer and ML brain.

## 2. Bit-Packing Design

### 2.1 Storage: `Vec<u32>` per faction per layer

```
50×50 grid = 2,500 cells
2,500 cells ÷ 32 bits/u32 = 79 integers per grid
```

Each faction has TWO grids:
- `visible[faction_id]: Vec<u32>` — cells currently seen (cleared each tick)
- `explored[faction_id]: Vec<u32>` — cells ever seen (cumulative, never cleared)

Total memory per faction: 79 × 2 × 4 bytes = **632 bytes**. Ten factions = 6.3 KB.

### 2.2 Bit Operations

```rust
fn set_bit(grid: &mut [u32], index: usize) {
    grid[index / 32] |= 1 << (index % 32);
}

fn get_bit(grid: &[u32], index: usize) -> bool {
    (grid[index / 32] >> (index % 32)) & 1 == 1
}

fn clear_all(grid: &mut [u32]) {
    grid.iter_mut().for_each(|v| *v = 0);
}
```

### 2.3 Cell Index Mapping

```
cell_x = ⌊world_x / cell_size⌋
cell_y = ⌊world_y / cell_size⌋
cell_index = cell_y × grid_width + cell_x
```

## 3. Visibility Update System

### 3.1 Per-Tick Algorithm

```
1. Clear all visible grids (explored persists)
2. For each entity with VisionRadius:
   a. Compute vision range in cell coordinates (AABB)
   b. For each cell in AABB with dist ≤ vision_radius:
      - Set visible[faction][cell] = 1
      - Set explored[faction][cell] = 1
   c. Wall occlusion: skip cells behind terrain walls (Bresenham raycasting)
```

### 3.2 Wall-Aware Vision

When a wall cell is between an entity and a target cell, the target cell is NOT
visible. Uses Bresenham line from entity cell to target cell, checking each
intermediate cell for `hard_cost == u16::MAX`.

### 3.3 Cell Deduplication

Multiple entities of the same faction may light up the same cell. The `set_bit`
operation is idempotent — no deduplication logic needed. Setting a bit that's
already 1 is a no-op.

## 4. Two-Layer State Model

| Layer | Cleared | Purpose |
|:---|:---|:---|
| `visible` | Every tick | "What can I see RIGHT NOW?" |
| `explored` | Never (manual reset only) | "What have I EVER seen?" |

**For the debug visualizer:**
- Visible cells → full brightness
- Explored-but-not-visible → dimmed ("fog")
- Never explored → completely dark

**For the ML brain:**
- Visible enemy entities → included in state snapshot
- Explored-but-invisible enemies → excluded (information asymmetry)
- Never-explored → excluded

## 5. Cross-System Integration

### 5.1 Flow Field (Study 004 + 006)
Flow fields only use visible enemy positions as goals.

### 5.2 ZMQ State Snapshot
Enemy entities are filtered: only entities in the brain's visible cells are
included in the `StateSnapshot` sent to Python.

### 5.3 WebSocket Sync
Visible and explored grids are sent as raw `Vec<u32>` arrays per active fog faction.

## 6. Information Asymmetry for ML

This is the core design motivation. The ML macro-brain makes decisions under
**partial observability**:

- It does NOT know where all enemies are
- It only sees enemies in its visible cells
- It must decide between **exploring** (sending scouts) and **exploiting** (attacking known positions)
- The explore-exploit tradeoff is a Partially Observable Markov Decision Process (POMDP)

Without fog of war, the ML problem degenerates to a fully observed MDP, which
is trivially solvable with standard reinforcement learning.
