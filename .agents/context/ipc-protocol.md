# IPC Protocol Reference (v3.1)

> **Audience:** Agents working on Python env, Rust bridge code, or training pipeline.
> **Binding keywords:** `ipc`, `bridge`, `zmq`, `directive`, `snapshot`, `payload`, `protocol`

> [!IMPORTANT]
> This document describes the CURRENT protocol. Legacy formats (team strings, FLANK_LEFT actions) 
> are obsolete. See `features.md` for migration history.

---

## 1. ZMQ Communication Model

**Pattern:** REQ/REP over TCP (`tcp://127.0.0.1:5555`)

```
Python (REQ)                    Rust (REP)
    |                               |
    |--- macro_directives --------->|  (Python sends commands)
    |                               |  Rust simulates N ticks
    |<-- state_snapshot ------------|  (Rust sends new state)
    |                               |
    (repeat every ai_eval_interval_ticks)
```

- Python is the REQ client, Rust is the REP server
- Each exchange: Python sends directives → Rust simulates → Rust replies with snapshot
- Exchange rate: every `ai_eval_interval_ticks` (default: 30 ticks = 0.5 seconds at 60 TPS)

---

## 2. Reset Payload (Python → Rust)

Sent once at the start of each episode to configure the Rust simulation:

```json
{
  "type": "reset",
  "world_width": 500.0,
  "world_height": 500.0,
  "spawns": [
    {
      "faction_id": 0,
      "count": 50,
      "x": 80.0,
      "y": 250.0,
      "spread": 60.0,
      "stats": [{ "index": 0, "value": 100.0 }]
    },
    {
      "faction_id": 1,
      "count": 50,
      "x": 400.0,
      "y": 80.0,
      "spread": 50.0,
      "stats": [{ "index": 0, "value": 200.0 }]
    }
  ],
  "interaction_rules": [
    {
      "source_faction": 0,
      "target_faction": 1,
      "range": 25.0,
      "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
    }
  ],
  "removal_rules": [
    { "stat_index": 0, "threshold": 0.0, "condition": "LessOrEqual" }
  ],
  "movement": {
    "max_speed": 60.0,
    "steering_factor": 5.0,
    "separation_radius": 6.0,
    "separation_weight": 1.5,
    "flow_weight": 1.0
  },
  "terrain": {
    "hard_costs": [100, 100, 65535, ...],
    "soft_costs": [100, 40, 100, ...],
    "width": 25,
    "height": 25,
    "cell_size": 20.0
  },
  "fog_enabled": true,
  "abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "zone_modifier_duration_ticks": 1500
  },
  "max_entity_ecp": 200.0
}
```

**Key fields:**
- `spawns[].stats[]` — initial stat values per entity (index 0 = HP by convention)
- `terrain` — optional, omitted for flat maps (defaults to all-100 costs)
- `fog_enabled` — controls whether entities outside visibility are filtered from snapshot
- `max_entity_ecp` — (optional, f32) maximum HP for ECP normalization. Auto-computed by Python from spawn stats each episode. Used by Rust for `DensityConfig.max_entity_ecp` to normalize ECP density maps to [0, 1]. Defaults to 100.0 if omitted.

### SpawnConfig (expanded)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| faction_id | u32 | yes | — | Faction ownership |
| count | u32 | yes | — | Number to spawn |
| x, y | f32 | yes | — | Spawn center |
| spread | f32 | yes | — | Spawn radius |
| stats | SpawnStatEntry[] | no | [] | Initial stat values |
| unit_class_id | u32 | no | 0 | Unit class (0 = generic) |

### CombatRulePayload (expanded)

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| source_faction | u32 | yes | — | Who attacks |
| target_faction | u32 | yes | — | Who gets hit |
| range | f32 | yes | — | Fixed combat range |
| effects | StatEffect[] | yes | — | Stat modifications |
| source_class | u32? | no | null | Filter: source must be this class |
| target_class | u32? | no | null | Filter: target must be this class |
| range_stat_index | usize? | no | null | Source stat index for dynamic range |
| mitigation | MitigationPayload? | no | null | Target damage mitigation |
| cooldown_ticks | u32? | no | null | Per-entity cooldown between fires |

### MitigationPayload

| Field | Type | Description |
|-------|------|-------------|
| stat_index | usize | Target stat providing mitigation value |
| mode | string | "PercentReduction" or "FlatReduction" |

---

## 3. Macro Directives (Python → Rust)

Sent every eval interval. Contains directives for ALL factions (brain + bots):

```json
{
  "type": "macro_directives",
  "directives": [
    {
      "directive": "UpdateNavigation",
      "follower_faction": 0,
      "target": { "type": "Waypoint", "x": 300.0, "y": 200.0 }
    },
    { "directive": "Idle" },
    { "directive": "Idle" }
  ]
}
```

### Directive Types

| Directive | Fields | Description |
|-----------|--------|-------------|
| `Idle` | — | No-op (faction continues current behavior) |
| `UpdateNavigation` | `follower_faction`, `target` | Set/update navigation (flow field recompute) |
| `Hold` | `faction_id` | Remove navigation rule (stop movement) |
| `ActivateBuff` | `faction`, `modifiers[]`, `duration_ticks`, `targets` | Apply stat modifiers to a faction |
| `Retreat` | `faction`, `retreat_x`, `retreat_y` | Navigate to retreat waypoint |
| `SetZoneModifier` | `target_faction`, `x`, `y`, `radius`, `cost_modifier` | Pheromone (negative) or repellent (positive) |
| `SplitFaction` | `source_faction`, `new_sub_faction`, `percentage`, `epicenter` | Split N% of faction's entities into new sub-faction |
| `MergeFaction` | `source_faction`, `target_faction` | Merge sub-faction back into parent |
| `SetAggroMask` | `source_faction`, `target_faction`, `allow_combat` | Enable/disable combat between faction pair |

### Navigation Target Types

```json
{ "type": "Waypoint", "x": 300.0, "y": 200.0 }
{ "type": "Faction", "faction_id": 1 }
```

### Zone Modifier Details

```json
{
  "directive": "SetZoneModifier",
  "target_faction": 0,
  "x": 200.0, "y": 300.0,
  "radius": 60.0,
  "cost_modifier": -50
}
```
- Negative = pheromone (attract), positive = repellent (repel)
- Duration is configurable via `zone_modifier_duration_ticks` in `ability_config` (reset payload). Training default: 1500 ticks (~25 seconds).

---

## 4. State Snapshot (Rust → Python)

Returned after each directive exchange:

```json
{
  "type": "state_snapshot",
  "tick": 1234,
  "summary": {
    "faction_counts": { "0": 48, "1": 45, "2": 18 },
    "faction_centroids": {
      "0": [150.3, 200.1],
      "1": [400.0, 80.0]
    }
  },
  "density_maps": {
    "0": [0.0, 0.02, 0.15, ...],
    "1": [0.0, 0.0, 0.5, ...],
    "2": [0.0, 0.0, 0.0, ...]
  },
  "fog_explored": [1.0, 1.0, 0.0, ...],
  "fog_visible": [1.0, 0.0, 0.0, ...]
}
```

**Key fields:**
- `faction_counts` — integer count of alive entities per faction
- `density_maps` — normalized heatmaps per faction (grid cells), 0.0–1.0
- `fog_explored` — binary grid: 1.0 = cell has been explored, 0.0 = never seen
- `fog_visible` — binary grid: 1.0 = cell is currently visible, 0.0 = fog

> [!NOTE]
> When `fog_enabled: true`, density maps for enemy factions are **masked by fog_visible**.
> Cells not currently visible show 0.0 density even if enemies are there.
> Python uses `LKPBuffer` to remember last-known positions from previously visible cells.

---

## 5. WebSocket Protocol (Rust ↔ Browser)

### SyncDelta (Rust → Browser)

Broadcast every tick. Delta-only by default; full snapshot every 60 ticks.
Entities are included when Position, Velocity, OR StatBlock change.

```json
{
  "type": "SyncDelta",
  "tick": 1235,
  "moved": [
    { "id": 1, "x": 151.0, "y": 201.0, "dx": 1.5, "dy": -0.5, "faction_id": 0, "stats": [100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] }
  ],
  "removed": [42, 99, 107]
}
```

#### Debug-Telemetry Fields (every 6 ticks, requires `debug-telemetry` feature)

| Field | Type | Description |
|-------|------|-------------|
| `telemetry` | `PerfTelemetry?` | Per-system microsecond timings |
| `visibility` | `VisibilitySync?` | Fog-of-war explored/visible grids |
| `zone_modifiers` | `ZoneModifierSync[]?` | Active pheromone/repellent zones |
| `active_sub_factions` | `u32[]?` | Currently active sub-faction IDs |
| `aggro_masks` | `{"src_tgt": bool}?` | Combat enable/disable per faction pair |
| `ml_brain` | `MlBrainSync?` | Python connection status, last directive |
| `density_heatmap` | `{faction_id: float[]}?` | Ch0/Ch1: Raw entity density per faction (50×50 grid, normalized 0–1) |
| `ecp_density_maps` | `{faction_id: float[]}?` | Ch7: Effective Combat Power density (hp × damage_mult, clamped to grid, floor of 1.0 per entity) |

> [!NOTE]
> `ecp_density_maps` differs from `density_heatmap`: density counts entities per cell,
> while ECP weights each entity by `hp × damage_mult`. ECP clamps out-of-bounds entities
> to the nearest grid edge (never drops factions). Minimum contribution per entity = 1.0.

### Commands (Browser → Rust)

```json
{ "type": "command", "cmd": "spawn_wave", "params": { "faction": 0, "amount": 500, "x": 100.0, "y": 100.0 } }
{ "type": "command", "cmd": "pause" }
{ "type": "command", "cmd": "resume" }
{ "type": "command", "cmd": "set_speed", "params": { "multiplier": 2.0 } }
```

---

## 6. Python Action → Directive Mapping

**File:** `macro-brain/src/env/actions.py`

The Python env produces a `MultiDiscrete([8, 2500])` action. The first element selects the action type, the second is a flattened spatial coordinate `(x * grid_w + y)`.

| Action Index | Name | Directive(s) Produced |
|-------------|------|-----------------------|
| 0 | Hold | `Idle` |
| 1 | AttackCoord | `UpdateNavigation(Waypoint)` |
| 2 | DropPheromone | `SetZoneModifier(cost=-50)` |
| 3 | DropRepellent | `SetZoneModifier(cost=+200)` |
| 4 | SplitToCoord | `SplitFaction(30%)` + `UpdateNavigation` |
| 5 | MergeBack | `MergeFaction` |
| 6 | Retreat | `Retreat(x, y)` |
| 7 | Scout | `SplitFaction(10%)` + `UpdateNavigation` |

### Action Unlock Schedule (Curriculum)

| Stage | New Actions Unlocked |
|-------|---------------------|
| 0 | Hold, AttackCoord |
| 2 | DropPheromone |
| 3 | DropRepellent |
| 4 | Scout |
| 5 | SplitToCoord, MergeBack |
| 6 | Retreat |

Locked actions are masked out via `action_masks()` — the policy cannot select them.
