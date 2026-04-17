# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_B1_rust_directives` |
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

1. **Create** `tasks_pending/task_B1_rust_directives_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_B1_rust_directives
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

### Rule 5: Live System Safety
The training pipeline (`macro-brain` → ZMQ → `micro-core`) may be running during your execution.

- **Rust tasks:** DO NOT run `cargo build` or `cargo test` — use `cargo check` only. Full testing is QA's job in a controlled window. See `execution-lifecycle.md` Step 1b.
- **Python tasks:** ONLY ADD new optional code. Never modify existing signatures or remove symbols. All new fields must have defaults.
- **Profile files:** DO NOT modify any `.json` profile in `macro-brain/profiles/`.

### Rule 6: Workspace Hygiene
If you need to create standalone temporary `.py`, `.rs`, or `.js` test scripts to quickly verify logic, simulate API calls, or run isolated experiments during development, **DO NOT dump them in the repository root or project source folders**. You MUST create and place all scratch files inside `.agents/scratch/`. Keep the main source tree clean.



## Context Loading (Tier-Dependent)

**If your tier is `basic`:**
- Your Task Brief IS your complete instruction.
- Pay **STRICT** attention to the import paths, package names, and method signatures
  listed in the brief — these are verified correct. Do NOT substitute with
  names from your training data. If the brief says `use bevy::prelude::Transform`,
  use EXACTLY that — do not hallucinate alternatives.
- Implement the code based on the instructions. You are expected to write the
  implementation, not copy-paste it.

**If your tier is `standard`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
5. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
6. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
7. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

**If your tier is `advanced`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ALL `context/*` sub-files listed in your `Context_Bindings` below
5. **If `research_digest.md` is in your bindings, read it THOROUGHLY** —
   this contains structured codebase knowledge (types, integration points, patterns, gotchas)
   that you need for implementation decisions
6. **If `strategy_brief.md` is in your bindings, read it for design rationale** —
   understand WHY the design decisions were made, not just what to build
7. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
8. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
9. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints
10. You have **AUTONOMY** to make implementation decisions within the architectural
   constraints defined in your brief and the research digest. Your brief describes
   goals and constraints, not step-by-step instructions — you are expected to reason
   through the implementation.

_No additional context bindings specified._

---

## Task Brief

# Task B1: Rust Directives + FactionTacticalOverrides Resource

- **Task_ID:** `B1_rust_directives`
- **Execution_Phase:** 1 (Brain Phase B)
- **Model_Tier:** `advanced`
- **Live_System_Impact:** `destructive` — modifies directive enum + executor

## Target_Files
- `micro-core/src/bridges/zmq_protocol/directives.rs` — MODIFY
- `micro-core/src/systems/directive_executor/executor.rs` — MODIFY
- `micro-core/src/config/tactical_overrides.rs` — NEW
- `micro-core/src/config/mod.rs` — MODIFY (add `pub mod tactical_overrides;`)
- `micro-core/src/main.rs` — MODIFY (init resource)
- `micro-core/src/bridges/zmq_bridge/reset.rs` — MODIFY (clear on reset)

## Dependencies
- None (first task in Brain Phase B)

## Context_Bindings
- `strategy_brief.md` — §Engine Capability Inventory, §Action Space v3
- `research_digest.md` — §SplitFaction, §TacticalBehavior, §Integration Points (Fix 2 + Fix 3)
- `implementation_plan_brain_v3.md` — Contracts 1, 2
- `.agents/skills/rust-code-standards/SKILL.md`

## Strict_Instructions

### 1. Add `class_filter` to SplitFaction (directives.rs)

Add `class_filter: Option<u32>` with `#[serde(default)]` to the `SplitFaction` variant:

```rust
SplitFaction {
    source_faction: u32,
    new_sub_faction: u32,
    percentage: f32,
    epicenter: [f32; 2],
    #[serde(default)]
    class_filter: Option<u32>,  // None = all classes, Some(id) = only class_id
}
```

### 2. Add SetTacticalOverride variant (directives.rs)

```rust
SetTacticalOverride {
    faction: u32,
    behavior: Option<TacticalBehaviorPayload>,  // None = clear override
}
```

The `TacticalBehaviorPayload` enum already exists in `zmq_protocol/payloads.rs` — verify it has `Kite { trigger_radius, weight }` and `PeelForAlly { ... }` variants. Use `#[serde(tag = "type")]` for JSON discrimination.

### 3. Create FactionTacticalOverrides resource (config/tactical_overrides.rs)

```rust
use bevy_ecs::prelude::*;
use std::collections::HashMap;
use crate::config::unit_registry::TacticalBehavior;

#[derive(Resource, Default, Debug)]
pub struct FactionTacticalOverrides {
    pub overrides: HashMap<u32, Vec<TacticalBehavior>>,
}
```

Register in `config/mod.rs`: `pub mod tactical_overrides;`

### 4. Handle class_filter in SplitFaction executor (executor.rs)

The current `faction_query` is `Query<(Entity, &Position, &mut FactionId)>`. Add `&UnitClassId` to the query:

```rust
// Updated query tuple:
Query<(Entity, &Position, &mut FactionId, &UnitClassId)>
```

In the SplitFaction handler, filter candidates by class:

```rust
.filter(|(_, _, f, class_id)| {
    f.0 == source_faction
        && class_filter.map_or(true, |cf| class_id.0 == cf)
})
```

**Verify** that all other directive handlers using `faction_query` are compatible (MergeFaction, Retreat). They should destructure with `(entity, _, faction, _)` — the extra `&UnitClassId` is ignored.

### 5. Handle SetTacticalOverride in executor (executor.rs)

Add a new match arm:

```rust
MacroDirective::SetTacticalOverride { faction, behavior } => {
    match behavior {
        Some(payload) => {
            let behaviors = payload_to_tactical_behaviors(payload);
            tactical_overrides.overrides.insert(faction, behaviors);
        }
        None => {
            tactical_overrides.overrides.remove(&faction);
        }
    }
}
```

You'll need to convert `TacticalBehaviorPayload` → `Vec<TacticalBehavior>`. The conversion already exists in `zmq_bridge` for spawn configs — find and reuse the pattern.

Add `ResMut<FactionTacticalOverrides>` to the executor system params.

### 6. MergeFaction cleanup (executor.rs)

In the `MergeFaction` handler block (after removing nav_rules, zones, buffs, aggro, interaction_rules), add:

```rust
tactical_overrides.overrides.remove(&source_faction);
```

### 7. ResetEnvironment cleanup (reset.rs)

In reset handler, clear all overrides:

```rust
tactical_overrides.overrides.clear();
```

### 8. Init resource (main.rs)

Add to the app builder:

```rust
.init_resource::<FactionTacticalOverrides>()
```

## Verification_Strategy
```
Test_Type: unit + compilation
Acceptance_Criteria:
  - "SplitFaction with class_filter: null splits all classes (backward compat)"
  - "SplitFaction with class_filter: 1 only splits entities with UnitClassId(1)"
  - "SetTacticalOverride with behavior: Kite inserts into FactionTacticalOverrides"
  - "SetTacticalOverride with behavior: null removes from FactionTacticalOverrides"
  - "MergeFaction removes tactical overrides for source faction"
  - "ResetEnvironment clears all tactical overrides"
  - "cargo check passes"
  - "cargo test passes (all 251+ tests)"
  - "cargo clippy clean"
Suggested_Test_Commands:
  - "cd micro-core && cargo check"
  - "cd micro-core && cargo test"
  - "cd micro-core && cargo clippy -- -D warnings"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._
