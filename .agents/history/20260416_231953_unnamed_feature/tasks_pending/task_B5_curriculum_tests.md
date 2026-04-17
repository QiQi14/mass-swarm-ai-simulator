# Task B5: Curriculum v3 + Tests + Context Docs

- **Task_ID:** `B5_curriculum_tests`
- **Execution_Phase:** 3 (Brain Phase B — depends on B3, B4)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `destructive` — changes action names and unlock table

## Target_Files
- `macro-brain/src/training/curriculum.py` — MODIFY
- `macro-brain/profiles/tactical_curriculum.json` — MODIFY
- `macro-brain/tests/test_actions.py` — MODIFY (rewrite for 3D actions)
- `.agents/context/training/stages.md` — MODIFY

## Dependencies
- B3 + B4 complete (action space and env integration finalized)

## Context_Bindings
- `implementation_plan_brain_v3.md` — Contract 5 (action names + unlock stages)
- `strategy_brief.md` — §Stage Unlock Order (Revised)

## Strict_Instructions

### 1. Update curriculum.py ACTION_NAMES

Update any `ACTION_NAMES` references in curriculum.py to match the v3 naming:
```python
ACTION_NAMES = [
    "Hold", "AttackCoord", "ZoneModifier", "SplitToCoord",
    "MergeBack", "SetPlaystyle", "ActivateSkill", "Retreat"
]
```

### 2. Update tactical_curriculum.json actions array

```json
"actions": [
    { "index": 0, "name": "Hold", "unlock_stage": 0 },
    { "index": 1, "name": "AttackCoord", "unlock_stage": 0 },
    { "index": 2, "name": "ZoneModifier", "unlock_stage": 2 },
    { "index": 3, "name": "SplitToCoord", "unlock_stage": 5 },
    { "index": 4, "name": "MergeBack", "unlock_stage": 5 },
    { "index": 5, "name": "SetPlaystyle", "unlock_stage": 5 },
    { "index": 6, "name": "ActivateSkill", "unlock_stage": 7 },
    { "index": 7, "name": "Retreat", "unlock_stage": 6 }
]
```

Also update meta.description to reference `MultiDiscrete([8, 2500, 4])`.

### 3. Rewrite test_actions.py for 3D actions

All tests must pass `np.array([action_type, coord, modifier])` instead of 2D arrays.

**Required test updates:**
- `test_hold_action`: action = `np.array([0, 125, 0])`
- `test_attack_coord`: action = `np.array([1, 125, 0])`
- `test_zone_modifier_attract`: action = `np.array([2, 125, 0])` → cost=-50
- `test_zone_modifier_repel`: action = `np.array([2, 125, 1])` → cost=+200
- `test_split_to_coord_all`: action = `np.array([3, 125, 0])` → class_filter=null
- `test_split_to_coord_class1`: action = `np.array([3, 125, 2])` → class_filter=1
- `test_merge_back`: action = `np.array([4, 125, 0])`
- `test_set_playstyle_aggressive`: action = `np.array([5, 0, 0])` → aggro on + clear override
- `test_set_playstyle_passive`: action = `np.array([5, 0, 1])` → aggro off
- `test_set_playstyle_kite`: action = `np.array([5, 0, 2])` → SetTacticalOverride Kite
- `test_set_playstyle_no_subs`: action = `np.array([5, 0, 0])` with no subs → Hold
- `test_retreat`: action = `np.array([7, 125, 0])`
- `test_negative_path`: action = `np.array([999, 125, 0])` → Hold

**Remove old tests:** `test_drop_pheromone`, `test_drop_repellent`, `test_scout`

### 4. Update stages.md

Update the action vocabulary section to reflect v3:
- Document 3-dimension encoding `[action, coord, modifier]`
- Document new actions: ZoneModifier (merged), SetPlaystyle, removed Scout
- Update unlock table per strategy_brief.md §Stage Unlock Order

## Verification_Strategy
```
Test_Type: unit
Acceptance_Criteria:
  - "All test_actions.py tests pass with 3D action arrays"
  - "ZoneModifier replaces separate pheromone/repellent tests"
  - "SetPlaystyle tests cover all 4 modifiers + no-subs fallback"
  - "tactical_curriculum.json has 8 actions with correct names and unlock stages"
  - "Full test suite passes: pytest tests/ -v"
Suggested_Test_Commands:
  - "cd macro-brain && .venv/bin/python -m pytest tests/test_actions.py -v"
  - "cd macro-brain && .venv/bin/python -m pytest tests/ -v"
```
