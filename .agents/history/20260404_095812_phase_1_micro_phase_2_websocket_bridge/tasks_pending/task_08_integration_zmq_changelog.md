# Changelog: Task 08 - Integration ZMQ

## Touched Files
- `micro-core/src/main.rs`

## Contract Fulfillment
- Added `ZmqBridgePlugin` to the main app setup.
- Added `StatesPlugin` from `bevy_state::app::StatesPlugin` to resolve the `StateTransition` schedule missing panic.
- Gated `movement_system` with `.run_if(in_state(SimState::Running))`.
- Preserved all MP2 WS additions.
- Ungated systems `tick_counter_system`, `log_system`, `smoke_test_exit_system`, and `ws_sync_system`.

## Deviations/Notes
- Included `StatesPlugin` for state management to work properly.
- As the ZMQ timeout is 5 seconds and `SimState::WaitingForAI` is entered at tick 30 (0.5s), the fallback might happen slightly after tick 300 (which is at 5.0s if running accurately at 60 TPS). Thus, the `smoke_test_exit_system` might trigger closely before or at the time of the ZMQ timeout.
