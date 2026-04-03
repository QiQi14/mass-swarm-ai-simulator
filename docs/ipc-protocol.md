# IPC Protocol Reference

> Complete message schema for all inter-process communication bridges.

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

Sent every N ticks (default ≈2 Hz). Contains the full simulation state for RL inference.

```json
{
  "type": "state_snapshot",
  "tick": 1234,
  "world_size": { "w": 1000.0, "h": 1000.0 },
  "entities": [
    { "id": 1, "x": 150.3, "y": 200.1, "team": "swarm", "health": 0.85 },
    { "id": 2, "x": 400.0, "y": 300.5, "team": "defender", "health": 1.0 }
  ],
  "summary": {
    "swarm_count": 5000,
    "defender_count": 200,
    "avg_swarm_health": 0.72,
    "avg_defender_health": 0.91
  }
}
```

> **Note:** The `entities` array may contain all entities or a sampled subset depending on scale. The `summary` field provides aggregate stats for the neural network's observation space regardless.

### Macro Action (Python → Rust)

High-level strategic command returned in the ZMQ REP.

```json
{
  "type": "macro_action",
  "action": "FLANK_LEFT",
  "params": { "intensity": 0.8 }
}
```

**Action Vocabulary:**

| Action | Effect |
|--------|--------|
| `HOLD` | Maintain current behavior, no change to flow field |
| `TRIGGER_FRENZY` | All-out aggressive swarm push toward defenders |
| `FLANK_LEFT` | Redirect swarm flow field to left flank |
| `FLANK_RIGHT` | Redirect swarm flow field to right flank |
| `RETREAT` | Pull swarm back toward spawn zone |
| `SURROUND` | Redistribute flow field to encircle defender positions |

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
    { "id": 1, "x": 150.3, "y": 200.1, "team": "swarm", "health": 0.85 }
  ]
}
```

### Delta Update (Rust → Browser)

Broadcast frequently. Contains only entities that changed since the last broadcast.

```json
{
  "type": "delta_update",
  "tick": 1235,
  "spawned": [
    { "id": 501, "x": 10.0, "y": 20.0, "team": "swarm", "health": 1.0 }
  ],
  "moved": [
    { "id": 1, "x": 151.0, "y": 201.0 }
  ],
  "died": [42, 99, 107]
}
```

**Array contents:**
- `spawned` — New entities with full data (id, position, team, health)
- `moved` — Existing entities that changed position (id + new x/y only)
- `died` — Entity IDs that were removed from the simulation

### Command (Browser → Rust)

User-initiated control actions sent from the Debug Visualizer's UI controls.

```json
{
  "type": "command",
  "cmd": "spawn_wave",
  "params": { "team": "swarm", "amount": 500, "x": 100.0, "y": 100.0 }
}
```

**Available Commands:**

| Command | Params | Effect |
|---------|--------|--------|
| `spawn_wave` | `team`, `amount`, `x`, `y` | Spawn entities at position |
| `pause` | — | Pause the simulation tick loop |
| `resume` | — | Resume the simulation tick loop |
| `set_speed` | `multiplier` | Change tick speed (e.g., `2.0` = double speed) |
| `kill_all` | `team` | Remove all entities of a team |

---

## Data Type Reference

| Field | Type | Constraints |
|-------|------|-------------|
| `id` | `u32` | Globally unique within a simulation session |
| `x`, `y` | `f32` | World coordinates. Origin: top-left `(0, 0)`. Positive Y = down. |
| `health` | `f32` | Normalized: `0.0` (dead) to `1.0` (full health) |
| `team` | `string` | `"swarm"` or `"defender"` (lowercase) |
| `tick` | `u64` | Monotonically increasing simulation tick counter |
| `w`, `h` | `f32` | World dimensions in simulation units |

---

## Serialization Evolution

| Phase | Format | Why |
|-------|--------|-----|
| **1–3** | JSON | Human-readable, inspectable in DevTools and REPLs |
| **4** | Bincode or MessagePack | Binary format for 10K+ entity throughput |

The JSON schema above remains the canonical reference. Binary serialization preserves the same structure — only the encoding changes.
