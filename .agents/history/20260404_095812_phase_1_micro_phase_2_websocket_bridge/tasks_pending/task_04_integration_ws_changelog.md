# Changelog: Task 04 Integration WS

## Touched Files
- Modified: `micro-core/src/main.rs`

## Contract Fulfillment
- Initialized Tokio broadcast channel (`tx`, `rx`).
- Spawned isolated OS thread running Tokio async runtime to execute `ws_server::start_server(rx)`.
- Exported `tx` as a Bevy resource via `BroadcastSender`.
- Added `micro_core::systems::ws_sync::ws_sync_system` to Bevy `Update` systems.
- Configured conditional execution for `smoke_test_exit_system` by checking `std::env::args()` for `--smoke-test`.

## Deviations/Notes
- Verified via `cargo test` and `cargo run -- --smoke-test` (exited cleanly at tick 300).
- Ready for QA verification for WebSocket connection stream.
