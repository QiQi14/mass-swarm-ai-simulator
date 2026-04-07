# IPC Protocol Reference

> Complete message schema for all inter-process communication bridges.  
> Last updated: Phase 3 (2026-04-06)

## Overview

All messages are JSON objects with a mandatory `"type"` field as the discriminator. Three bridges exist:

| Bridge | Protocol | Direction | Port |
|--------|----------|-----------|------|
| AI Bridge | ZeroMQ REQ/REP | Rust ↔ Python | `tcp://localhost:5555` |
| Debug Broadcast | WebSocket | Rust → Browser | `ws://localhost:8080` |
| Debug Control | WebSocket | Browser → Rust | `ws://localhost:8080` |

---

## AI Bridge (Rust ↔ Python)

### State Snapshot (Rust → Python)

Sent every 30 ticks (~2 Hz). Contains the full simulation state for RL inference.

```json
{
  "type": "state_snapshot",
  "tick": 1234,
  "world_size": { "w": 1000.0, "h": 1000.0 },
  "entities": [
    { "id": 1, "x": 150.3, "y": 200.1, "faction": 0, "health": 0.85 }
  ],
  "summary": {
    "swarm_count": 5000,
    "defender_count": 200,
    "avg_swarm_health": 0.72,
    "avg_defender_health": 0.91
  },
  "active_sub_factions": [101, 102],
  "active_zones": [
    { "target_faction": 0, "x": 300.0, "y": 400.0, "radius": 100.0, "cost_modifier": -50.0 }
  ],
  "aggro_masks": { "101_1": false },
  "density_maps": {
    "0": [0.0, 0.1, 0.3, "...2500 floats (50x50)"],
    "1": ["..."]
  },
  "intervention_active": true
}
```

### AiResponse Envelope (Python → Rust)

Python responds with a discriminated union. Two variants:

#### Directive (Normal Tick)
```json
{
  "type": "directive",
  "directive": { "TriggerFrenzy": { "faction": 0, "speed_multiplier": 1.5, "duration_ticks": 120 } }
}
```

#### Reset Environment (Episode Start)
```json
{
  "type": "reset_environment",
  "terrain": {
    "hard_costs": [100, 100, 65535, "...2500 values"],
    "soft_costs": [100, 100, 50, "...2500 values"],
    "width": 50,
    "height": 50,
    "cell_size": 20.0
  },
  "spawns": [
    { "faction": 0, "count": 50, "x": 200.0, "y": 500.0 },
    { "faction": 1, "count": 50, "x": 800.0, "y": 500.0 }
  ]
}
```

> **Note:** ResetEnvironment is atomic — Rust applies terrain + respawns before returning the first snapshot. This guarantees Markov Decision Process consistency.

### MacroDirective Vocabulary (8 Actions)

| # | Directive | Parameters | Effect |
|---|-----------|-----------|--------|
| 0 | `Hold` | — | No-op, maintain current behavior |
| 1 | `UpdateNavigation` | `follower_faction`, `target` | Change flow field target (Faction or Waypoint) |
| 2 | `TriggerFrenzy` | `faction`, `speed_multiplier`, `duration_ticks` | Temporary speed buff |
| 3 | `Retreat` | `faction`, `retreat_x`, `retreat_y` | Set waypoint to retreat position |
| 4 | `SetZoneModifier` | `target_faction`, `x`, `y`, `radius`, `cost_modifier` | Attract/repel via Dijkstra cost overlay |
| 5 | `SplitFaction` | `source_faction`, `new_sub_faction`, `percentage`, `epicenter` | Divide faction for pincer maneuvers |
| 6 | `MergeFaction` | `source_faction`, `target_faction` | Reunite split sub-factions |
| 7 | `SetAggroMask` | `source_faction`, `target_faction`, `allow_combat` | Toggle combat between specific factions |

### NavigationTarget Variants
```json
// Chase a faction
{ "Faction": { "faction_id": 1 } }

// Navigate to a point
{ "Waypoint": { "x": 500.0, "y": 300.0 } }
```

---

## Debug Bridge (Rust ↔ Browser)

### Full Sync (Rust → Browser)

Sent once when a browser client first connects. Contains the complete world state.

```json
{
  "type": "full_sync",
  "tick": 1234,
  "world_size": { "w": 1000.0, "h": 1000.0 },
  "entities": [
    { "id": 1, "x": 150.3, "y": 200.1, "faction": 0, "health": 0.85 }
  ],
  "terrain": {
    "hard_costs": ["..."],
    "soft_costs": ["..."],
    "width": 50,
    "height": 50,
    "cell_size": 20.0
  }
}
```

### Delta Update (Rust → Browser)

Broadcast at 10 TPS. Contains only entities that changed since the last broadcast.

```json
{
  "type": "delta_update",
  "tick": 1235,
  "spawned": [
    { "id": 501, "x": 10.0, "y": 20.0, "faction": 0, "health": 1.0 }
  ],
  "moved": [
    { "id": 1, "x": 151.0, "y": 201.0 }
  ],
  "died": [42, 99, 107]
}
```

### Command (Browser → Rust)

User-initiated control actions sent from the Debug Visualizer's UI controls.

```json
{
  "type": "command",
  "cmd": "spawn_wave",
  "params": { "faction": 0, "amount": 500, "x": 100.0, "y": 100.0 }
}
```

**Available Commands:**

| Command | Params | Effect |
|---------|--------|--------|
| `spawn_wave` | `faction`, `amount`, `x`, `y` | Spawn entities at position |
| `pause` | — | Pause the simulation tick loop |
| `resume` | — | Resume the simulation tick loop |
| `step` | `ticks` | Step N ticks then pause |
| `set_speed` | `multiplier` | Change tick speed (e.g., `2.0` = double) |
| `kill_all` | `faction` | Remove all entities of a faction |
| `set_terrain` | `x`, `y`, `hard`, `soft` | Paint a terrain cell |
| `clear_terrain` | — | Reset all terrain to passable |
| `save_scenario` | — | Serialize current state to JSON |
| `load_scenario` | `scenario` | Restore a saved state |

---

## Data Type Reference

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `u32` | Globally unique within a simulation session |
| `x`, `y` | `f32` | World coordinates. Origin: top-left `(0, 0)`. Positive Y = down. |
| `health` | `f32` | Normalized: `0.0` (dead) to `1.0` (full health) |
| `faction` | `u32` | `0` = swarm (AI-controlled), `1` = defender (heuristic), `101+` = sub-factions |
| `tick` | `u64` | Monotonically increasing simulation tick counter |
| `w`, `h` | `f32` | World dimensions in simulation units |

---

## Serialization

| Phase | Format | Why |
|-------|--------|-----|
| **1–3** | JSON | Human-readable, inspectable in DevTools and REPLs |
| **4** | Bincode or MessagePack | Binary format for 10K+ entity throughput |

The JSON schema above remains the canonical reference. Binary serialization preserves the same structure — only the encoding changes.
