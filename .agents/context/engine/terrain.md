# Terrain & Zones

## 5. Terrain System

**File:** `micro-core/src/terrain.rs`

Terrain is a 2D grid of costs, used by the flow field pathfinder to compute optimal movement paths.

### Two Cost Layers

| Layer | Purpose | Used By |
|-------|---------|---------|
| `hard_costs: Vec<u32>` | Pathfinding obstacles | Flow field (Dijkstra) — higher cost = harder to path through |
| `soft_costs: Vec<u32>` | Movement speed modifiers | Movement system — affects entity speed on that cell |

### Cost Tiers (from profile thresholds)

```json
"terrain_thresholds": {
  "impassable_threshold": 65535,
  "destructible_min": 60001
}
```

| Value | Meaning | Flow Field Behavior |
|-------|---------|-------------------|
| `100` | Default passable ground | Normal pathing (cost = 100) |
| `40` | Mud / slow zone (soft_cost) | Entities move slower |
| `300` | Danger zone (hard_cost) | Pathfinder avoids but CAN path through if no alternative |
| `60001–65534` | Destructible wall (hard_cost) | Very high cost — pathfinder strongly avoids |
| `65535` | Permanent impassable wall | Pathfinder treats as BLOCKED — never routes through |

> [!IMPORTANT]
> **Default terrain cost is 100, NOT 0.** The flow field Dijkstra uses costs additively.
> A cost of 0 means "free" (teleportation). A cost of 100 is the standard baseline for open ground.
> When generating flat terrain (no obstacles), fill both `hard_costs` and `soft_costs` with `100`.

### Terrain Payload Format (sent in ZMQ reset)

```json
{
  "hard_costs": [100, 100, 65535, ...],
  "soft_costs": [100, 40, 100, ...],
  "width": 30,
  "height": 30,
  "cell_size": 20.0
}
```
- Array is row-major: `index = y * width + x`
- `cell_size` maps grid coords to world coords: `world_x = grid_x * cell_size`

---

## 6. Pheromone & Repellent (Zone Modifiers)

**File:** `micro-core/src/systems/directive_executor/executor.rs` (SetZoneModifier)

Pheromone and Repellent work by temporarily modifying terrain costs around a world coordinate.

### How It Works

Python sends a `SetZoneModifier` directive:
```json
{
  "directive": "SetZoneModifier",
  "target_faction": 0,
  "x": 200.0, "y": 300.0,
  "radius": 60.0,
  "cost_modifier": -50
}
```

> **Duration:** The ticks_remaining is NOT set per-directive. It comes from
> `BuffConfig.zone_modifier_duration_ticks` which is set during environment
> reset via `AbilityConfigPayload.zone_modifier_duration_ticks`.

- **Negative `cost_modifier`** = Pheromone (attract) — reduces terrain cost, making the flow field prefer this area
- **Positive `cost_modifier`** = Repellent — increases terrain cost, making the flow field avoid this area
- **`ticks_remaining`** — configurable via `zone_modifier_duration_ticks` in `AbilityConfigPayload` (sent in reset). Default: 120 ticks (~2 seconds). Tactical curriculum uses 1500 ticks (~25 seconds / ~10 RL steps).
- Zones modify the flow field on next recalculation

### Flow Field Impact

The flow field pathfinder adds zone modifiers to the base terrain cost:
```
effective_cost = hard_cost + sum(zone_modifiers_at_cell)
```
So a pheromone (cost_modifier = -50) on a 100-cost cell → 50 cost → preferred path.
A repellent (+200) on a 100-cost cell → 300 cost → avoided path.

---

## 11. Fog of War

**File:** `micro-core/src/visibility.rs`, `micro-core/src/systems/visibility.rs`

- **Explored grid:** Bit-packed grid tracking which cells have ever been seen (persists)
- **Visible grid:** Which cells are currently in line-of-sight of any faction entity (recomputed each tick)
- **Wall-aware BFS:** Visibility spreads from each entity up to vision range, blocked by impassable terrain
- **ZMQ filtering:** When fog is enabled, the state snapshot only includes entities in visible cells

### Fog Schedule in Curriculum

| Stages 0–3 | Stages 4+ |
|-------------|-----------|
| `fog_enabled: false` | `fog_enabled: true` |
| Full visibility | Partial observation |

---

## 13. ECP Density Maps (Threat Visualization)

**File:** `micro-core/src/systems/state_vectorizer.rs` (builder), `micro-core/src/systems/ws_sync.rs` (broadcast)

### What It Does

ECP (Effective Combat Power) density maps provide a spatial heatmap of combat threat intensity. Unlike raw density maps (entity headcount per cell), ECP weights each entity by its configurable primary stat and damage multiplier. The stat used is fully configurable via `DensityConfig.ecp_stat_index` — the engine has no concept of "HP".

### Calculation

```
For each alive entity:
  primary_stat = stat_block[ecp_stat_index]   ← configurable (default: stat[0])
  ecp = max(primary_stat × damage_mult, 1.0)  ← floor prevents zero-contribution
  cell = clamp(position / cell_size, 0, grid_max-1)  ← clamped, never skipped
  grid[faction][cell] += ecp

Normalize: grid[faction][cell] / max_ecp_per_cell → [0.0, 1.0]
```

**Key design decisions:**
- `max(ecp, 1.0)` — alive entities always contribute at least presence-level ECP, even if primary_stat=0 (about to be removed) or damage_mult=0 (fully debuffed)
- `ecp_stat_index: Option<usize>` — `Some(0)` reads stat[0] (default), `None` produces zero ECP maps (no primary stat configured)
- Coordinate **clamping** instead of skipping — prevents entire factions from being absent from the HashMap when entities spawn near world boundaries

### WS Broadcast

ECP maps are broadcast every 6 ticks inside the `SyncDelta` message under the `ecp_density_maps` field (requires `debug-telemetry` feature).

**Architecture note:** The `ws_sync_system` bundles all 12 debug-telemetry resources into a `WsSyncTelemetry` SystemParam struct to stay under Bevy's 16-parameter limit. See knowledge item `gotcha_bevy_16_parameter_limit.md`.

### Grid Configuration

| Parameter | Source | Default |
|-----------|--------|---------|
| `grid_w` | `SimulationConfig.world_width / flow_field_cell_size` | 50 (1000/20) |
| `grid_h` | `SimulationConfig.world_height / flow_field_cell_size` | 50 (1000/20) |
| `max_ecp_per_cell` | `DensityConfig.max_density × DensityConfig.max_entity_ecp` | Profile-driven |

> [!IMPORTANT]
> **`max_entity_ecp` is auto-computed from spawns each episode.** The Python `swarm_env.py` computes `_max_primary_stat` from the spawn stats during `reset()` (using the stat index derived from `removal_rules[0].stat_index`) and sends it to Rust via the reset payload. This replaces the previous hardcoded `* 100.0`.
>
> Formula: `max_ecp_per_cell = max_density × max_primary_stat × max_damage_mult`
> Default `max_damage_mult` = 1.0 (no buff active at episode start).

---