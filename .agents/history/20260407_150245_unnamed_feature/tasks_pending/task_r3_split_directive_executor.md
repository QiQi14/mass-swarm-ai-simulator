# Task R3: Split `directive_executor.rs`

- **Task_ID:** task_r3_split_directive_executor
- **Execution_Phase:** 1 (parallel)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files
- `micro-core/src/systems/directive_executor.rs` → DELETE (becomes directory)
- `micro-core/src/systems/directive_executor/mod.rs` [NEW]
- `micro-core/src/systems/directive_executor/executor.rs` [NEW]
- `micro-core/src/systems/directive_executor/buff_tick.rs` [NEW]
- `micro-core/src/systems/directive_executor/zone_tick.rs` [NEW]
- `micro-core/src/systems/mod.rs` (update `mod directive_executor` declaration)

## Dependencies
- None (Phase 1)

## Context_Bindings
- `context/conventions`
- `skills/rust-code-standards`

## Strict_Instructions

### Goal
Convert `directive_executor.rs` (507 lines, 3 systems) into a directory module. **Pure refactor — zero logic changes.**

### Step 1: Create `executor.rs`

Move from the original file:
- `LatestDirective` struct
- `directive_executor_system` function
- Associated tests for directive execution

Add module doc:
```rust
//! # Directive Executor
//!
//! Processes `MacroDirective` commands from the Python macro-brain.
//! Maps directives to ECS state mutations (navigation, buffs, retreats, splits).
```

### Step 2: Create `buff_tick.rs`

Move:
- `buff_tick_system` function
- Any buff-related tests

Add module doc:
```rust
//! # Buff Tick System
//!
//! Decrements active buff group durations each tick.
//! Removes expired groups and starts cooldowns.
```

### Step 3: Create `zone_tick.rs`

Move:
- `zone_tick_system` function
- Any zone-related tests

Add module doc:
```rust
//! # Zone Tick System
//!
//! Decrements zone modifier durations each tick.
//! Removes expired zone modifiers.
```

### Step 4: Create `mod.rs`

```rust
//! # Directive Executor Module
//!
//! Three ECS systems that process macro-brain directives and manage timed effects.

mod executor;
mod buff_tick;
mod zone_tick;

pub use executor::{LatestDirective, directive_executor_system};
pub use buff_tick::buff_tick_system;
pub use zone_tick::zone_tick_system;
```

### Step 5: Update `systems/mod.rs`

The `mod directive_executor;` declaration stays the same — Rust automatically resolves a directory module via `mod.rs`.

### Step 6: Delete original `directive_executor.rs`

### Step 7: Verify

```bash
cd micro-core && cargo test directive_executor && cargo test buff_tick && cargo test zone_tick && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test)
  Acceptance_Criteria:
    - "All existing tests pass"
    - "executor.rs under 300 lines"
    - "buff_tick.rs under 150 lines"
    - "zone_tick.rs under 100 lines"
    - "cargo clippy clean"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test directive && cargo clippy"
