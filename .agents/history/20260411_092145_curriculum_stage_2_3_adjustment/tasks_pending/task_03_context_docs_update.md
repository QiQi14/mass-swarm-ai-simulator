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
