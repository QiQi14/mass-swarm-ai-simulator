# Changelog: Task 03 WS Bidirectional Commands

## Touched Files
- `micro-core/src/bridges/ws_protocol.rs` (Modified)
- `micro-core/src/systems/ws_sync.rs` (Modified)
- `micro-core/src/config.rs` (Modified)
- `micro-core/src/bridges/ws_server.rs` (Modified)
- `micro-core/src/systems/ws_command.rs` (Created)
- `micro-core/src/systems/mod.rs` (Modified)
- `micro-core/src/systems/movement.rs` (Modified)
- `micro-core/src/main.rs` (Modified)

## Contract Fulfillment
- Extended `EntityState` with `dx` and `dy` for velocity vector rendering, as defined in the Phase 1 Micro-Phase 4 API contract.
- Introduced `WsCommand` structure to correctly decode incoming JSON directives from the debugger via websockets.
- Added simulation control resources (`SimPaused`, `SimSpeed`, `SimStepRemaining`).
- Migrated `start_server` to act dually (broadcasting and forwarding incoming commands to Bevy via an mpsc channel). 
- Integrated parsing logical routines via `ws_command_system` to execute `toggle_sim`, `step`, `spawn_wave`, `set_speed`, and `kill_all`.
- Created an inline `step_tick_system` working alongside `SimStepRemaining` and `SimPaused` gating logic to enable finite frame pacing.
- Modified movement scaling dynamically by using `SimSpeed.multiplier` natively in `movement_system`.

## Deviations / Notes
- The RNG velocity injection upon `spawn_wave` is simulated with uniform boundaries (between -1.0 to 1.0) using the standard `rand` crate generator logic mapped identically to the `initial_spawn_system`.
- Movement physics correctly integrates arbitrary user speeds using the multiplier component dynamically at runtime loop updates inside the Rust backend.
