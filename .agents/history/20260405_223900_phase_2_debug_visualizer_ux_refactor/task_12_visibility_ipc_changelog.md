# Task 12 Changelog: Visibility IPC

## Touched Files
- `micro-core/src/systems/visibility.rs` (NEW)
- `micro-core/src/systems/mod.rs` (MODIFIED)
- `micro-core/src/systems/ws_sync.rs` (MODIFIED)
- `micro-core/src/bridges/ws_protocol.rs` (MODIFIED)
- `micro-core/src/bridges/zmq_protocol.rs` (MODIFIED)
- `micro-core/src/bridges/zmq_bridge/systems.rs` (MODIFIED)

## Contract Fulfillment
- **Cell-Centric Deduplication & Wall-Aware Vision:** Implemented `visibility_update_system` grouping entities into cells and running flood-fill per cell. It ensures walls (hard_cost == u16::MAX) cannot be "seen through", conforming to the integer distance limits.
- **WebSocket Synchronization:** Added `VisibilitySync` variant, capturing bit-packed visible and explored grid. Updated `ws_sync.rs` to propagate this payload to visually tracking UI listeners precisely every 6 ticks (10 TPS). 
- **ZMQ Architecture & Information Asymmetry:** Extended `StateSnapshot` payload with FoW and terrain fields. Updated `build_state_snapshot()` logic inside `zmq_bridge/systems.rs` so the AI brain only receives its own active entities and the enemy entities correctly visible in its grid. 

## Deviations/Notes
- `ActiveFogFaction` was imported from `crate::systems::ws_command::ActiveFogFaction` because task 13 code (`ws_command.rs`) had already implicitly stubbed this type in advance.
- We added two specific tests in `zmq_bridge/systems.rs` using a dummy capture system to correctly verify FoW filtering and "own entities" logic safely within a mock app world. 
- Warning suppressions and `#[cfg(feature = "debug-telemetry")]` guards were strictly added matching `Visibility` usage inside `ws_sync` to ensure backward-compatible `--no-default-features` builds.
