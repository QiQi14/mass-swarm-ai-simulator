# Changelog for task_07_ipc_visualizer_upgrades

## Touched Files
- `micro-core/Cargo.toml` [MODIFIED]
- `micro-core/src/plugins/mod.rs` [CREATED]
- `micro-core/src/plugins/telemetry.rs` [CREATED]
- `micro-core/src/lib.rs` [MODIFIED]
- `micro-core/src/bridges/ws_protocol.rs` [MODIFIED]
- `micro-core/src/systems/ws_sync.rs` [MODIFIED]
- `micro-core/src/systems/ws_command.rs` [MODIFIED]
- `debug-visualizer/index.html` [MODIFIED]
- `debug-visualizer/style.css` [MODIFIED]
- `debug-visualizer/visualizer.js` [MODIFIED]

## Contract Fulfillment
- Extended `Cargo.toml` with `debug-telemetry` feature flag.
- Created `TelemetryPlugin` and `PerfTelemetry` resource via `plugins/telemetry.rs`.
- Created `flow_field_broadcast_system` handling N-faction `FlowFieldSync` payload generation at ~2 TPS.
- Updated `ws_protocol.rs` with conditionally compiled `FlowFieldSync` and updated `SyncDelta` message.
- Updated `ws_sync.rs` system to handle `PerfTelemetry` conditionally, broadcasting `removed` events and draining them. Tests updated for newly added required resources.
- Updated `ws_command.rs` adding `set_faction_mode` command which modifies `FactionBehaviorMode` resource dynamically.
- Upgraded Web UI (`index.html`, `style.css`) incorporating dual-canvas overlays, floating connection panel, performance chart, and telemetry sparklines.
- Upgraded JS visualization (`visualizer.js`) to support Flow Field cache and arrows overlay, dead entity fading animations, dynamic faction toggle buttons, performance bars, view panning with mouse, health bars, and click-to-inspect mechanism.

## Deviations/Notes
- The type `PerfTelemetry` inside `telemetry.rs` is NOT placed under `#[cfg(feature = "debug-telemetry")]` so that `Option<ResMut<PerfTelemetry>>` is properly resolved as a Bevy signature even in production, making it truly a zero-cost wrapper around type definitions, avoiding compiler errors.
- Applied `#[cfg(feature = "debug-telemetry")]` strictly to the inner blocks evaluating execution logic within `ws_sync.rs`.
- Fixed implicit requirement on `TickCounter` and `SimulationConfig` paths for `plugins/telemetry.rs` depending on where it lived.

## Human Interventions
None.
