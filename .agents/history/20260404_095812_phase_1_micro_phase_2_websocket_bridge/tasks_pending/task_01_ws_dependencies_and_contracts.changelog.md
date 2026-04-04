# Task Changelog: task_01_ws_dependencies_and_contracts

## Summary
Initialized the WebSocket bridge foundations by adding required crate dependencies and defining the core IPC protocol DTOs.

## Changes

### `micro-core/Cargo.toml`
- Added `tokio` (v1.51) with multi-thread and sync features.
- Added `tokio-tungstenite` (v0.29) for WebSocket server support.
- Added `futures-util` (v0.3) for stream handling.

### `micro-core/src/lib.rs`
- Exported `pub mod bridges;`.
- Updated module-level documentation to include `crate::bridges` in the dependency list.

### `micro-core/src/bridges/mod.rs` (NEW)
- Barrel file for bridge modules.
- Exported `pub mod ws_protocol;`.

### `micro-core/src/bridges/ws_protocol.rs` (NEW)
- Defined `EntityState` struct for serializing entity ID, Position, and Team.
- Defined `WsMessage` enum with `SyncDelta` variant for broadcasting tick-based updates.
- Added `serde` tag "type" for discriminator-based JSON serialization.

## Verification Results
- **Command:** `cargo check`
- **Output:** `Finished dev profile [unoptimized + debuginfo] target(s) in 0.28s`
- **Status:** PASS
