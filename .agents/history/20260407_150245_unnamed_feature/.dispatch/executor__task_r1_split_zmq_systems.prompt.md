# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_r1_split_zmq_systems` |
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

1. **Create** `tasks_pending/task_r1_split_zmq_systems_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_r1_split_zmq_systems
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

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

