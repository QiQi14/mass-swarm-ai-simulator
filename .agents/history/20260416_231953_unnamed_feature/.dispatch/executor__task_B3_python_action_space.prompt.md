# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_B3_python_action_space` |
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

1. **Create** `tasks_pending/task_B3_python_action_space_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_B3_python_action_space
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

# Task B3: Python Action Space v3

- **Task_ID:** `B3_python_action_space`
- **Execution_Phase:** 2 (Brain Phase B — depends on B1 contracts)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `destructive` — changes action space shape

## Target_Files
- `macro-brain/src/env/spaces.py` — MODIFY
- `macro-brain/src/env/actions.py` — MODIFY

## Dependencies
- B1 complete: Rust directive JSON contracts for SplitFaction(class_filter) and SetTacticalOverride

## Context_Bindings
- `implementation_plan_brain_v3.md` — Contracts 1, 2, 4, 5 (action table, mask shape, directive JSON)
- `strategy_brief.md` — §Action Table, §Modifier Detail, §Action → Directive Mapping

## Strict_Instructions

### 1. Rewrite spaces.py

**Action constants (rename + reorder):**
```python
ACTION_HOLD = 0
ACTION_ATTACK_COORD = 1
ACTION_ZONE_MODIFIER = 2      # merged Pheromone + Repellent
ACTION_SPLIT_TO_COORD = 3
ACTION_MERGE_BACK = 4
ACTION_SET_PLAYSTYLE = 5      # NEW
ACTION_ACTIVATE_SKILL = 6
ACTION_RETREAT = 7

NUM_ACTIONS = 8
MODIFIER_DIM = 4              # modifier values 0-3

ACTION_NAMES = [
    "Hold", "AttackCoord", "ZoneModifier", "SplitToCoord",
    "MergeBack", "SetPlaystyle", "ActivateSkill", "Retreat"
]

SPATIAL_ACTIONS = {ACTION_ATTACK_COORD, ACTION_ZONE_MODIFIER, ACTION_SPLIT_TO_COORD, ACTION_RETREAT, ACTION_ACTIVATE_SKILL}
```

**make_action_space():**
```python
def make_action_space():
    return MultiDiscrete([NUM_ACTIONS, MAX_GRID_WIDTH * MAX_GRID_WIDTH, MODIFIER_DIM])
```

**Modifier masks per action type:**
```python
MODIFIER_MASKS = {
    ACTION_HOLD: [True, False, False, False],          # only mod=0
    ACTION_ATTACK_COORD: [True, False, False, False],  # only mod=0
    ACTION_ZONE_MODIFIER: [True, True, False, False],  # 0=attract, 1=repel
    ACTION_SPLIT_TO_COORD: [True, True, True, True],   # 0=all, 1/2/3=class
    ACTION_MERGE_BACK: [True, False, False, False],
    ACTION_SET_PLAYSTYLE: [True, True, True, True],    # 0=aggro, 1=passive, 2=kite, 3=clear
    ACTION_ACTIVATE_SKILL: [True, True, True, True],   # skill index 0-3
    ACTION_RETREAT: [True, False, False, False],
}
```

### 2. Full rewrite of actions.py — multidiscrete_to_directives()

**New signature:**
```python
def multidiscrete_to_directives(
    action: np.ndarray,       # shape (3,): [action_type, flat_coord, modifier]
    brain_faction: int,
    active_sub_factions: list[int],
    enemy_factions: list[int] | None = None,
) -> tuple[list[dict], dict | None]:
```

**Action → Directive mapping for each action type:**

- **ACTION_HOLD (0):** `Hold { faction_id: brain_faction }`
- **ACTION_ATTACK_COORD (1):** `UpdateNavigation { follower: brain_faction, target: Waypoint(x, y) }`
- **ACTION_ZONE_MODIFIER (2):**
  - mod=0: `SetZoneModifier { cost_modifier: -50 }` (attract/pheromone)
  - mod=1: `SetZoneModifier { cost_modifier: +200 }` (repel)
- **ACTION_SPLIT_TO_COORD (3):**
  - `SplitFaction { class_filter: None if mod==0 else mod-1, percentage: 0.3 }`
  - `UpdateNavigation { follower: sub_id, target: Waypoint(x, y) }`
- **ACTION_MERGE_BACK (4):** `MergeFaction { source: active_sub_factions[0], target: brain_faction }`
- **ACTION_SET_PLAYSTYLE (5):** Targets `active_sub_factions[-1]` (most recent sub)
  - mod=0: `SetAggroMask(sub, enemies, true)` + `SetTacticalOverride(sub, null)` [aggressive]
  - mod=1: `SetAggroMask(sub, enemies, false)` [passive]
  - mod=2: `SetTacticalOverride(sub, Kite { trigger_radius: 80, weight: 5 })` [kite]
  - mod=3: `SetTacticalOverride(sub, null)` + `SetAggroMask(sub, enemies, true)` [clear]
- **ACTION_ACTIVATE_SKILL (6):** `ActivateBuff { faction: brain, modifiers: skills[mod] }`
- **ACTION_RETREAT (7):** `Retreat { faction: brain, retreat_x, retreat_y }`

**Fallback:** Unknown action_type → Hold.
**SetPlaystyle with no active subs → Hold (no-op).**

### 3. Remove Scout action

The old `ACTION_SCOUT` (7) is removed. Scout behavior = `SplitToCoord(class=midline) + SetPlaystyle(passive)`. Remove all Scout-specific code (aggro mask logic moved into SetPlaystyle).

### 4. Coordinate decode

Keep the same flat_coord → (grid_x, grid_y) → world_coord logic. The grid is still 50×50.

## Verification_Strategy
```
Test_Type: unit
Acceptance_Criteria:
  - "make_action_space() returns MultiDiscrete([8, 2500, 4])"
  - "ACTION_ZONE_MODIFIER with mod=0 produces SetZoneModifier { cost: -50 }"
  - "ACTION_ZONE_MODIFIER with mod=1 produces SetZoneModifier { cost: +200 }"
  - "ACTION_SPLIT_TO_COORD with mod=0 produces SplitFaction { class_filter: null }"
  - "ACTION_SPLIT_TO_COORD with mod=2 produces SplitFaction { class_filter: 1 }"
  - "ACTION_SET_PLAYSTYLE with mod=2 produces SetTacticalOverride { behavior: Kite }"
  - "ACTION_SET_PLAYSTYLE with no active subs falls back to Hold"
  - "Unknown action type falls back to Hold"
Suggested_Test_Commands:
  - "cd macro-brain && .venv/bin/python -m pytest tests/test_actions.py -v"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._
