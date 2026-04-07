# Task R1: Split `zmq_bridge/systems.rs`

- **Task_ID:** task_r1_split_zmq_systems
- **Execution_Phase:** 1 (parallel)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files
- `micro-core/src/bridges/zmq_bridge/mod.rs`
- `micro-core/src/bridges/zmq_bridge/systems.rs`
- `micro-core/src/bridges/zmq_bridge/reset.rs` [NEW]
- `micro-core/src/bridges/zmq_bridge/snapshot.rs` [NEW]

## Dependencies
- None (Phase 1)

## Context_Bindings
- `context/conventions` (File Organization rules)
- `skills/rust-code-standards` (Part 1: Comments, Part 4: File Organization)

## Strict_Instructions

### Goal
Split `systems.rs` (1098 lines) into 3 focused files. This is a **pure refactor** — zero logic changes. Every function signature, struct, and test must remain identical.

### Step 1: Create `reset.rs`

Move the following items from `systems.rs` to `reset.rs`:
- `PendingReset` struct
- `ResetRequest` struct
- `ResetRules` SystemParam struct
- `reset_environment_system` function
- All `#[cfg(test)]` tests that test reset logic (tests containing "reset" in name)

Add module doc comment:
```rust
//! # ZMQ Reset Handler
//!
//! Processes `ResetEnvironment` requests from the Python macro-brain.
//! Despawns all entities, applies terrain/combat/ability config, and respawns.
//!
//! ## Ownership
//! - **Task:** task_r1_split_zmq_systems
//! - **Contract:** implementation_plan.md → Task R1
//!
//! ## Depends On
//! - `crate::components::*`
//! - `crate::config::*`
//! - `crate::terrain::TerrainGrid`
```

### Step 2: Create `snapshot.rs`

Move the following from `systems.rs` to `snapshot.rs`:
- `build_state_snapshot` function
- Any `CapturedSnapshot` test resource
- `capture_snapshot_system` test helper
- All `#[cfg(test)]` tests that test snapshot building

Add module doc comment:
```rust
//! # State Snapshot Builder
//!
//! Constructs `StateSnapshot` from the current ECS state for ZMQ transmission.
//!
//! ## Ownership
//! - **Task:** task_r1_split_zmq_systems
//! - **Contract:** implementation_plan.md → Task R1
```

### Step 3: Update `systems.rs`

Remove the moved items. Keep ONLY:
- `ai_trigger_system`
- `ai_poll_system`
- Their associated tests

Update imports to reference the new modules.

### Step 4: Update `mod.rs`

Add the new modules and re-exports:
```rust
pub(crate) mod reset;
pub(crate) mod snapshot;
```

Re-export public items so external callers don't break:
```rust
pub use reset::{PendingReset, ResetRequest};
```

### Step 5: Verify

```bash
cd micro-core && cargo test && cargo clippy
```

All existing tests must pass. Zero logic changes.

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "All existing tests pass without modification"
    - "systems.rs is under 400 lines"
    - "reset.rs is under 400 lines"
    - "snapshot.rs is under 300 lines"
    - "Each file has module-level doc comment"
    - "cargo clippy passes with no warnings"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test zmq_bridge && cargo clippy"
