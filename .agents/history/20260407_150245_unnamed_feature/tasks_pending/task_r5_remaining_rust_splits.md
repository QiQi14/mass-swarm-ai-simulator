# Task R5: Remaining Rust — Split or Document

- **Task_ID:** task_r5_remaining_rust_splits
- **Execution_Phase:** 2 (after R1-R4)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files
- `micro-core/src/systems/flow_field_update.rs`
- `micro-core/src/systems/flow_field_safety.rs` [NEW — if splitting]
- `micro-core/src/systems/ws_command.rs`
- `micro-core/src/pathfinding/flow_field.rs`
- `micro-core/src/systems/movement.rs`
- `micro-core/src/terrain.rs`
- `micro-core/src/systems/mod.rs` (if adding new module)

## Dependencies
- Tasks R1, R2, R3, R4 (imports must be stable)

## Context_Bindings
- `context/conventions`
- `skills/rust-code-standards` (Part 2.8: Doc Tests, Part 4: File Organization)

## Strict_Instructions

### Goal
Handle all Rust files in the 400-753 line range. Files >600 must split. Files 400-600 get rationale comments. Add doc tests to `terrain.rs` pure helpers.

### Step 1: `flow_field_update.rs` (753 lines — MUST SPLIT)

This file exceeds 600 lines. Split the safety patch guards:

**Create `flow_field_safety.rs`:**
- Move all safety-patch related functions (Moses Effect Guard, Vaporization Guard, etc.) to a new file
- Keep the core `flow_field_update_system` in the original file

Update `systems/mod.rs`:
```rust
pub mod flow_field_safety;
```

### Step 2: `ws_command.rs` (581 lines — add rationale)

Add rationale comment at the top after the module doc:
```rust
//! **File Size Rationale:** This module is 580+ lines but contains only two tightly
//! coupled systems (`ws_command_system` + `step_tick_system`) that share the same
//! WS receiver channel. Splitting would fragment the ownership chain.
//! Split if a third concern is added or tests exceed 300 lines.
```

### Step 3: `flow_field.rs` (508 lines — add rationale)

```rust
//! **File Size Rationale:** This module implements a single Dijkstra-based flow field
//! algorithm. The 500+ lines are due to the integration field computation + inline tests.
//! All functions share the same `FlowField` data structure. Keep as single file.
```

### Step 4: `movement.rs` (447 lines — add rationale)

```rust
//! **File Size Rationale:** Single movement system with Boids steering behaviors.
//! Tests account for ~280 lines. All logic shares the same query and config.
//! Keep as single file per Rust convention (tests beside the code).
```

### Step 5: `terrain.rs` (396 lines — add doc tests)

Under 400, keep as-is. But add doc tests to pure helper functions:

- `TerrainGrid::is_wall` — doc test showing wall detection
- `TerrainGrid::is_destructible` — doc test showing tier logic
- `TerrainGrid::world_to_cell` — doc test showing coordinate conversion
- `TerrainGrid::damage_cell` — doc test showing cell damage + destruction

Remove corresponding simple tests from `#[cfg(test)]` if they become redundant with the doc tests.

### Step 6: Verify

```bash
cd micro-core && cargo test && cargo test --doc && cargo clippy
```

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Rust (cargo test + cargo test --doc)
  Acceptance_Criteria:
    - "flow_field_update.rs under 600 lines after split"
    - "flow_field_safety.rs exists with safety patches"
    - "ws_command.rs, flow_field.rs, movement.rs have rationale comments"
    - "terrain.rs has at least 4 doc test examples"
    - "All existing tests pass"
    - "cargo test --doc passes"
    - "cargo clippy clean"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test && cargo test --doc && cargo clippy"
