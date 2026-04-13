# Task R2: Split `zmq_protocol.rs`

- **Task_ID:** task_r2_split_zmq_protocol
- **Execution_Phase:** 1 (parallel)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files
- `micro-core/src/bridges/zmq_protocol.rs` → DELETE (becomes directory)
- `micro-core/src/bridges/zmq_protocol/mod.rs` [NEW]
- `micro-core/src/bridges/zmq_protocol/types.rs` [NEW]
- `micro-core/src/bridges/zmq_protocol/directives.rs` [NEW]
- `micro-core/src/bridges/zmq_protocol/payloads.rs` [NEW]

## Dependencies
- None (Phase 1)

## Context_Bindings
- `context/conventions`
- `skills/rust-code-standards`

## Strict_Instructions

### Goal
Convert `zmq_protocol.rs` (562 lines, 20+ types) from a single file into a directory module with 3 focused files. **Pure refactor — zero logic changes.**

### Step 1: Create directory `bridges/zmq_protocol/`

### Step 2: Create `types.rs` — State/snapshot types

Move these structs:
- `EntitySnapshot`
- `SummarySnapshot`
- `WorldSize`
- `ZoneModifierSnapshot`
- `StateSnapshot`

### Step 3: Create `directives.rs` — Action/directive enums

Move these items:
- `MacroAction`
- `NavigationTarget`
- `ModifierType`
- `StatModifierPayload`
- `MacroDirective`
- `AiResponse`

### Step 4: Create `payloads.rs` — Config/spawn payloads

Move these structs:
- `TerrainPayload`
- `CombatRulePayload`
- `StatEffectPayload`
- `MovementConfigPayload`
- `TerrainThresholdsPayload`
- `RemovalRulePayload`
- `AbilityConfigPayload`
- `SpawnConfig`
- `SpawnStatEntry`

### Step 5: Create `mod.rs` — Re-export everything

```rust
//! # ZMQ Protocol Types
//!
//! Defines all data contracts for the ZMQ bridge between micro-core and macro-brain.
//! Split into: state types, directive/action enums, and config payloads.

mod types;
mod directives;
mod payloads;

pub use types::*;
pub use directives::*;
pub use payloads::*;
```

### Step 6: Delete the original `zmq_protocol.rs` file

### Step 7: Verify NO import changes needed externally

Since `mod.rs` re-exports everything with `pub use *`, all existing `use crate::bridges::zmq_protocol::*` imports remain valid.

```bash
cd micro-core && cargo test && cargo clippy
```

### Doc Test Candidates

Add doc test examples to:
- `NavigationTarget` — show serde roundtrip for Faction/Waypoint variants
- `MacroDirective` — show JSON deserialization example

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "All existing tests pass"
    - "Each file is under 250 lines"
    - "External imports unchanged (pub use re-exports)"
    - "cargo clippy clean"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test && cargo clippy"
