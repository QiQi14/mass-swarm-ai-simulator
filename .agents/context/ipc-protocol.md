# IPC Protocol Reference

> **Audience:** Executor agents working on bridge code, message parsing, or serialization.
> **Binding keyword:** `ipc`, `bridge`, `zmq`, `websocket`, `message`, `protocol`

## Message Envelope

All IPC messages are JSON objects with a mandatory `"type"` field as the discriminator:

```json
{
  "type": "state_snapshot",
  "tick": 1234,
  "payload": { ... }
}
```

## Message Types

### Rust → Python (ZMQ REQ)

| Type | Sent Every | Payload |
|------|------------|---------|
| `state_snapshot` | Every N ticks (configurable, default ~2 Hz) | Full or compressed state for RL inference |

**State Snapshot Payload:**
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

### Python → Rust (ZMQ REP)

| Type | Description |
|------|-------------|
| `macro_action` | High-level strategic command for the swarm |

**Macro Action Payload:**
```json
{
  "type": "macro_action",
  "action": "FLANK_LEFT",
  "params": { "intensity": 0.8 }
}
```

**Action Vocabulary (Phase 3):**
- `HOLD` — Maintain current behavior
- `TRIGGER_FRENZY` — All-out aggressive swarm push
- `FLANK_LEFT` / `FLANK_RIGHT` — Redirect swarm flow field
- `RETREAT` — Pull swarm back to spawn zone
- `SURROUND` — Encircle defender positions

### Rust → Browser (WebSocket, broadcast)

| Type | Description |
|------|-------------|
| `delta_update` | Entities that changed since last broadcast |
| `full_sync` | Complete state dump (sent on initial connection) |

**Delta Update Payload:**
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

### Browser → Rust (WebSocket, command)

| Type | Description |
|------|-------------|
| `command` | User-initiated control action |

**Command Payload:**
```json
{
  "type": "command",
  "cmd": "spawn_wave",
  "params": { "team": "swarm", "amount": 500, "x": 100.0, "y": 100.0 }
}
```

**Commands (Phase 1):**
- `spawn_wave` — Spawn a group of entities at a position
- `pause` / `resume` — Toggle simulation tick loop
- `set_speed` — Change simulation speed multiplier (e.g., `{ "multiplier": 2.0 }`)
- `kill_all` — Remove all entities of a given team

## Data Types

| Field | Type | Notes |
|-------|------|-------|
| `id` | `u32` | Globally unique within a session |
| `x`, `y` | `f32` | Origin top-left `(0,0)`, positive Y = down |
| `health` | `f32` | Normalized `0.0` to `1.0` |
| `team` | `string` | `"swarm"` or `"defender"` |
| `tick` | `u64` | Monotonically increasing simulation tick counter |

## Serialization Roadmap

| Phase | Format | Library |
|-------|--------|---------|
| Phase 1–3 | JSON | `serde_json` (Rust), `json` (Python), native (JS) |
| Phase 4 | Bincode or MessagePack | `bincode` / `rmp-serde` (Rust), `msgpack` (Python) |

> [!NOTE]
> JSON is used during prototype phases for debuggability — messages can be inspected in browser DevTools and Python REPL. Binary formats are introduced in Phase 4 strictly for throughput at 10K+ entities.
