# Study Notes: 3-Tier Interactable Terrain

> **Problem:** How to encode terrain so that RL agents can learn to use terrain destruction as a tactical tool, while preventing them from breaking the simulation's core invariants.

---

## The Terrain Encoding

A single `u16` hard_cost value encodes three tiers:

```
 0 ─────── 100 ─────── 60,000 ─────── 60,001 ─────── 65,534 ─────── 65,535
 |  unused  | PASSABLE (Tier 0)       | DESTRUCTIBLE (Tier 1)      | PERMANENT (Tier 2)
 |          | Dijkstra cost = value   | Blocks pathfinding         | Moses Effect protected
 |          | Zone modifiers work     | Breakable by zone modifiers| Immune to ALL modification
```

### Constants
```rust
pub const TERRAIN_DESTRUCTIBLE_MIN: u16 = 60_001;
pub const TERRAIN_DESTRUCTIBLE_MAX: u16 = 65_534;
pub const TERRAIN_PERMANENT_WALL: u16 = u16::MAX; // 65_535
```

---

## Tier Behaviors

| Tier | Range | Pathfinding | Zone Modifiers | `damage_cell()` |
|------|-------|-------------|----------------|------------------|
| **0 (Passable)** | 100–60,000 | Cost = value (100 = normal) | ✅ Modifiable | No effect |
| **1 (Destructible)** | 60,001–65,534 | ∞ (blocked) | ✅ Can break | Reduces cost, collapses to Tier 0 |
| **2 (Permanent)** | 65,535 | ∞ (blocked) | ❌ Moses Effect | No effect |

### Soft Costs (Speed Modifier)
A separate `soft_costs` array controls movement speed:
- `100` = full speed (100%)
- `50` = half speed (swamp)
- `0` = stopped

Soft costs are independent of hard costs — a cell can be passable but slow (swamp).

---

## Moses Effect Guard

The Moses Effect is the invariant that permanent walls (Tier 2) can NEVER be modified. This prevents:
1. RL agents from learning to "delete" map boundaries
2. Zone modifiers from accidentally opening holes in containment walls
3. Terrain generators from overwriting critical geometry

### Implementation
```rust
// In flow_field_update_system:
if terrain.get_hard_cost(cell) == u16::MAX {
    continue; // Skip this cell — Moses Effect
}

// In damage_cell():
if cost == TERRAIN_PERMANENT_WALL {
    return false; // Immune
}
```

---

## Terrain Generator

The Python terrain generator produces procedural maps for Stage 2 curriculum training:

### Guarantees
1. **Spawn zones always clear** — 4-cell radius around (10,25) and (40,25)
2. **BFS connectivity** — Path guaranteed between spawn zones
3. **Fallback corridor** — If BFS fails, carves a 3-cell-wide horizontal corridor
4. **Mixed walls** — 40% destructible (Tier 1), 60% permanent (Tier 2)

### Payload Format (matches Rust `TerrainPayload`)
```json
{
    "hard_costs": [100, 100, 65535, ...],  // 2500 u16 values (50×50)
    "soft_costs": [100, 100, 50, ...],     // 2500 u16 values (speed %)
    "width": 50,
    "height": 50,
    "cell_size": 20.0
}
```

---

## Integration with RL

### Stage 1 (Flat Map)
- All cells = `100` (Tier 0 passable)
- Actions 4-7 masked (no terrain interaction)
- Agent learns combat dynamics only

### Stage 2 (Procedural)
- Random terrain injected via `ResetEnvironment` ZMQ message
- `SetZoneModifier` can attract entities through destructible walls
- Agent must learn when to destroy vs. navigate around
