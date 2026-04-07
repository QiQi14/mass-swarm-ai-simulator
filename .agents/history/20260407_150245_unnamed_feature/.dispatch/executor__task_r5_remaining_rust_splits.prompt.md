# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_r5_remaining_rust_splits` |
| Feature | Unnamed Feature |
| Tier    | standard |

---

## ⛔ MANDATORY PROCESS — ALL TIERS (DO NOT SKIP)

> **These rules apply to EVERY executor, regardless of tier. Violating them
> causes an automatic QA FAIL and project BLOCK.**

### Rule 1: Scope Isolation
- You may ONLY create or modify files listed in `Target_Files` in your Task Brief.
- If a file must be changed but is NOT in `Target_Files`, **STOP and report the gap** — do NOT modify it.
- NEVER edit `task_state.json`, `implementation_plan.md`, or any file outside your scope.

### Rule 2: Changelog (Handoff Documentation)
After ALL code is written and BEFORE calling `./task_tool.sh done`, you MUST:

1. **Create** `tasks_pending/task_r5_remaining_rust_splits_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_r5_remaining_rust_splits
   ```

> **⚠️ Calling `./task_tool.sh done` without creating the changelog file is FORBIDDEN.**

### Rule 3: No Placeholders
- Do not use `// TODO`, `/* FIXME */`, or stub implementations.
- Output fully functional, production-ready code.

### Rule 4: Human Intervention Protocol
During execution, a human may intercept your work and propose changes, provide code snippets, or redirect your approach. When this happens:

1. **ADOPT the concept, VERIFY the details.** Humans are exceptional at architectural vision but make detail mistakes (wrong API, typos, outdated syntax). Independently verify all human-provided code against the actual framework version and project contracts.
2. **TRACK every human intervention in the changelog.** Add a dedicated `## Human Interventions` section to your changelog documenting:
   - What the human proposed (1-2 sentence summary)
   - What you adopted vs. what you corrected
   - Any deviations from the original task brief caused by the intervention
3. **DO NOT silently incorporate changes.** The QA agent and Architect must be able to trace exactly what came from the spec vs. what came from a human mid-flight. Untracked changes are invisible to the verification pipeline.

---

## Context Loading (Tier-Dependent)

**If your tier is `basic`:**
- Skip all external file reading. Your Task Brief below IS your complete instruction.
- Implement the code exactly as specified in the Task Brief.
- Follow the MANDATORY PROCESS rules above (changelog + scope), then halt.

**If your tier is `standard` or `advanced`:**
1. Read `.agents/context.md` — Thin index pointing to context sub-files
2. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
3. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
4. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
5. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

_No additional context bindings specified._

---

## Task Brief

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

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

