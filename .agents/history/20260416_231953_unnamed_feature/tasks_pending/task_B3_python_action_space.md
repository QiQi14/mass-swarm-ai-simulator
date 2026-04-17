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
