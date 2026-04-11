# State Management & Networking

Located in `src/state.js`, `src/websocket.js`, and `src/config.js`.

## WebSocket Connection (`websocket.js`)

### How it works
1. Opens a WebSocket to `ws://localhost:8080` (the Rust micro-core WS server).
2. Receives `SyncDelta` messages containing entity state changes.
3. Every 6 ticks, receives debug-telemetry payloads (density maps, visibility, etc.).
4. Sends `WsCommand` messages upstream for user interactions (pause, speed, spawn).

### SyncDelta Processing
- **Delta ticks:** Only entities with changed Position, Velocity, OR StatBlock are included.
- **Full sync (every 60 ticks):** All entities are broadcast to handle late-connecting clients.
- **Entity format:** `{ id, x, y, dx, dy, faction_id, stats: [f32; 8] }`
- **Removals:** `removed: [entity_id, ...]` — IDs are deleted from the state map.

### Observation Channel Data (every 6 ticks)
| Field | JS State Variable | Description |
|-------|------------------|-------------|
| `density_heatmap` | `S.densityHeatmap` | `HashMap<faction_id, float[]>` — raw entity count per 50×50 grid cell |
| `ecp_density_maps` | `S.ecpDensityMaps` | `HashMap<faction_id, float[]>` — HP×damage_mult weighted density (Ch7 threat) |
| `visibility` | `S.fogExplored/fogVisible` | Bit-packed fog-of-war grids |
| `telemetry` | `S.perfTelemetry` | Per-system microsecond timings |

## State Container (`state.js`)

Flat ES module exports — no Redux or complex state managers.

### Key State Variables
- `entities: Map<ID, {x, y, dx, dy, faction_id, stats, has_override}>` — the entity registry
- `densityHeatmap` — raw density maps from Ch0/Ch1 overlays
- `ecpDensityMaps` — ECP maps for Ch7 threat overlay
- `showDensityHeatmap`, `showThreatDensity`, etc. — overlay toggle booleans

### Preventing Memory Leaks
When an entity dies, the `removed` array in SyncDelta triggers explicit `Map.delete()`. Without this, dead entities accumulate in browser heap over long training sessions.

### Stat Tracking (Inspector)
Each entity's `prevStats` snapshot is stored for delta-indicator computation (▲ buff / ▼ debuff). Stats are anonymous (S0, S1, ...) — the engine is contract-agnostic.
