# Task A5: Remove Stat Fallback with Warning Log - Changelog

## Touched Files
- `micro-core/src/bridges/zmq_bridge/reset.rs`
- `micro-core/src/bridges/zmq_protocol/payloads.rs`

## Contract Fulfillment
- Removed the hardcoded `HP=100` fallback in the simulation reset logic.
- Implemented a warning log (`println!`) that triggers when `SpawnConfig` has empty stats.
- Updated `SpawnConfig::stats` to default to an empty vector, resulting in an all-zero `StatBlock`.
- Updated the ZMQ protocol documentation for `SpawnConfig::stats` to reflect the new behavior.

## Deviations/Notes
- The changes strictly follow the "BEFORE/AFTER" snippets provided in the task brief.
- `cargo test bridges` and `cargo clippy` passed with zero failures/warnings.
- No human interventions were required or received during this task.
