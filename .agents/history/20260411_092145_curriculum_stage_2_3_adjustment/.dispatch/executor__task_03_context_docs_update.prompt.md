# AGENT ROLE: EXECUTION SPECIALIST

You are an **Execution Specialist** in a multi-agent DAG workflow.
You have been assigned ONE specific task. You implement it with surgical precision.

---

## Your Assignment

| Field   | Value |
|---------|-------|
| Task ID | `task_03_context_docs_update` |
| Feature | Curriculum Stage 2 & 3 Adjustment |
| Tier    | basic |

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

1. **Create** `tasks_pending/task_03_context_docs_update_changelog.md`
2. **Include in the changelog:**
   - **Touched Files:** A bulleted list of every file you created or modified.
   - **Contract Fulfillment:** Brief confirmation of the interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any edge cases you handled or deviations from the brief the QA agent should verify.
3. **Then and only then** run:
   ```bash
   ./task_tool.sh done task_03_context_docs_update
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

**If your tier is `standard` or `advanced`:**

> **CRITICAL FIRST STEP:** The Planner might omit critical skills or knowledge in your `Context_Bindings`. It is YOUR responsibility to self-heal missing context.
1. Read `.agents/skills/index.md` (Skills Catalog)
2. Read `.agents/knowledge/README.md` (Master Knowledge Index)
   *(If you discover a skill or knowledge domain relevant to your task that isn't in your `Context_Bindings`, **read it immediately** before starting.)*
3. Read `.agents/context.md` — Thin index pointing to context sub-files
4. Load ONLY the `context/*` sub-files listed in your `Context_Bindings` below
5. Scan `.agents/knowledge/` — Lessons from previous sessions relevant to your task
6. Read `.agents/workflows/execution-lifecycle.md` — Your 4-step execution loop
7. Read `.agents/rules/execution-boundary.md` — Scope and contract constraints

- `./.agents/context/engine-mechanics.md`
- `./.agents/context/ipc-protocol.md`
- `./.agents/context/training-curriculum.md`

---

## Task Brief

# Task 03: Context Documentation Updates

```yaml
Task_ID: task_03_context_docs_update
Execution_Phase: 3
Model_Tier: basic
Feature: "Curriculum Stage 2 & 3 Adjustment"
Dependencies:
  - task_01_rust_zone_duration_config
  - task_02_python_curriculum_actions
Context_Bindings: []
Target_Files:
  - .agents/context/engine-mechanics.md
  - .agents/context/ipc-protocol.md
  - .agents/context/training-curriculum.md
```

## Objective

Update three context documentation files to reflect the changes made in Tasks 01 and 02. These files are read by all future agents to understand the system.

---

## Strict Instructions

### Step 1: Update `engine-mechanics.md`

**File:** `.agents/context/engine-mechanics.md`

Update **Section 6** (Pheromone & Repellent — Zone Modifiers, around line 208-241).

Find the line:
```
- **`ticks_remaining: 120`** (hardcoded ~2 seconds) — zones are temporary
```

Replace with:
```
- **`ticks_remaining`** — configurable via `zone_modifier_duration_ticks` in `AbilityConfigPayload` (sent in reset). Default: 120 ticks (~2 seconds). Tactical curriculum uses 1500 ticks (~25 seconds / ~10 RL steps).
```

Also in the `SetZoneModifier` JSON example in the same section, add a note below it:

```
> **Duration:** The ticks_remaining is NOT set per-directive. It comes from
> `BuffConfig.zone_modifier_duration_ticks` which is set during environment
> reset via `AbilityConfigPayload.zone_modifier_duration_ticks`.
```

### Step 2: Update `ipc-protocol.md`

**File:** `.agents/context/ipc-protocol.md`

**2a.** Find the Zone Modifier Details line (line 152):
```
- Duration is hardcoded at 120 ticks (~2 seconds)
```

Replace with:
```
- Duration is configurable via `zone_modifier_duration_ticks` in `ability_config` (reset payload). Training default: 1500 ticks (~25 seconds).
```

**2b.** In the AbilityConfigPayload description area, or in the reset payload example (around lines 85-90), add `zone_modifier_duration_ticks` to the abilities section:

Under the existing `ability_config` fields in the reset payload example, add:
```json
"abilities": {
    "buff_cooldown_ticks": 180,
    "movement_speed_stat": 1,
    "combat_damage_stat": 2,
    "zone_modifier_duration_ticks": 1500
}
```

### Step 3: Update `training-curriculum.md`

**File:** `.agents/context/training-curriculum.md`

**3a.** In the Stage 3 section (around line 91-98), update the terrain description. Find:
```
- **Terrain:** Open field with 2-3 high-cost danger zones (hard_cost 300)
```

Replace with:
```
- **Terrain:** Open field with danger zones at NORMAL cost (hard_cost 100, soft_cost 40 visual markers). Flow field routes THROUGH traps by default. Agent must DropRepellent (+200) to create avoidance zones.
```

**3b.** In the same section, update the new action description. Find:
```
- **New action:** DropRepellent (cost modifier +200, repels flow field)
```

Verify this line is already correct. If it says `+50`, change to `+200`.

**3c.** Add a note to Stage 2 about terrain:

After the existing Stage 2 `- **Terrain:**` line, ensure it reads:
```
- **Terrain:** Two-path map with wall band through center
  - Top path: fast (cost 100) but trap group blocks it
  - Bottom path: slow (mud, soft_cost 40) but safe
  - Wall: permanent (65535) with gap at x=2-5
```

This should already match — verify and fix if needed.

---

## Anti-Patterns

- DO NOT rewrite entire sections — make surgical edits only
- DO NOT change information about stages 4-8 since they haven't been redesigned yet
- DO NOT remove any existing warnings or caution blocks

---

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: manual_steps
  Acceptance_Criteria:
    - "engine-mechanics.md Section 6 no longer says 'hardcoded' for zone duration"
    - "ipc-protocol.md reflects configurable zone duration"
    - "training-curriculum.md Stage 3 says hard_cost 100, not 300"
  Manual_Steps:
    - "Read .agents/context/engine-mechanics.md Section 6 — verify zone duration description"
    - "Read .agents/context/ipc-protocol.md zone modifier section — verify no 'hardcoded' language"
    - "Read .agents/context/training-curriculum.md Stage 3 — verify terrain description"
```

---

## Shared Contracts

_See `implementation_plan.md` for full contract definitions._

