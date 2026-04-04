# Task Changelog: task_06_zmq_protocol_cargo

## Changes

### 1. Added `zeromq` Dependency
- Updated `micro-core/Cargo.toml` to include `zeromq = "0.5"`.

### 2. Updated Bridges Module
- Updated `micro-core/src/bridges/mod.rs`.
- Added `pub mod zmq_protocol;` and `pub mod zmq_bridge;`.
- Updated module-level documentation with ownership details and dependencies for Phase 1 — Micro-Phase 3.

### 3. Implemented ZMQ Protocol Data Types
- Created `micro-core/src/bridges/zmq_protocol.rs`.
- Implemented serialization models for AI Bridge (Rust ↔ Python) IPC:
    - `EntitySnapshot`: Individual entity state.
    - `SummarySnapshot`: Aggregate stats for NN observations.
    - `WorldSize`: Dimensions of the simulation world.
    - `StateSnapshot`: Full state packet with JSON field renaming (`msg_type` -> `"type"`).
    - `MacroAction`: Action vocabulary from AI with flexible `params` object.
- Added comprehensive unit tests for serialization round-trips and field renaming logic.

### 4. Added ZMQ Bridge Placeholder
- Created `micro-core/src/bridges/zmq_bridge.rs` as a placeholder to allow module tree validation and subsequent task implementation.

## Verification Results

- **Cargo Check:** Passed.
- **Cargo Clippy:** Passed (zero warnings).
- **Cargo Test:** Passed `zmq_protocol` unit tests (4/4).
    - `test_state_snapshot_serialization_roundtrip`: OK
    - `test_state_snapshot_json_has_type_field`: OK
    - `test_macro_action_deserialization`: OK
    - `test_macro_action_with_params`: OK
