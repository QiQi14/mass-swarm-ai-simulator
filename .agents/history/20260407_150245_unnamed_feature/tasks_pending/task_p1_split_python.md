# Task P1: Split Python Profile + Env + Curriculum

- **Task_ID:** task_p1_split_python
- **Execution_Phase:** 1 (parallel)
- **Model_Tier:** standard
- **Feature:** File Splitting Refactor

## Target_Files
- `macro-brain/src/config/game_profile.py`
- `macro-brain/src/config/definitions.py` [NEW]
- `macro-brain/src/config/__init__.py`
- `macro-brain/src/env/swarm_env.py`
- `macro-brain/src/env/actions.py` [NEW]
- `macro-brain/src/env/__init__.py`
- `macro-brain/src/training/curriculum.py`
- `macro-brain/src/training/callbacks.py`
- `macro-brain/src/training/__init__.py`

## Dependencies
- None (Phase 1)

## Context_Bindings
- `context/conventions` (File Organization rules)

## Strict_Instructions

### Goal
Split 3 oversized Python files into focused modules. **Pure refactor — zero logic changes.** All existing tests must pass.

### Step 1: Split `game_profile.py` (373 lines)

**Create `definitions.py`** — extract ALL dataclasses:
- `WorldConfig`
- `FactionStats`
- `FactionConfig`
- `StatEffectConfig`
- `CombatRuleConfig`
- `CombatConfig`
- `MovementConfigDef`
- `TerrainThresholdsDef`
- `StatModifierDef`
- `ActivateBuffDef`
- `AbilitiesDef`
- `RemovalRuleDef`
- `ActionDef`
- `RewardWeights`
- `GraduationConfig`
- `DemotionConfig`
- `CurriculumStageConfig`
- `TrainingConfig`
- `ProfileMeta`

**Keep in `game_profile.py`:**
- `GameProfile` class (imports from `definitions`)
- `load_profile()` function
- `_parse_profile()` function

**Update `__init__.py`:**
```python
from .definitions import *
from .game_profile import GameProfile, load_profile
```

### Step 2: Split `swarm_env.py` (419 lines)

**Create `actions.py`** — extract the action-to-directive mapping:
- `_action_to_directive()` method → standalone function `action_to_directive(action, profile, ...)`
- Move the action constants/mapping logic

**Keep in `swarm_env.py`:**
- `SwarmEnv` class (calls `action_to_directive()` from `actions.py`)
- All ZMQ lifecycle methods (`_connect`, `_disconnect`, `reset`, `step`)
- Reward computation stays (already partially in `rewards.py`)

**Note:** If `_action_to_directive` is too tightly coupled to `self` state, keep it inline but extract the directive FORMAT constants into `actions.py`.

### Step 3: Split `curriculum.py` (421 lines)

**Move `CurriculumCallback` class** to `callbacks.py` (file already exists with other callbacks).

**Keep in `curriculum.py`:**
- `get_stage1_spawns`, `get_stage2_spawns`, `get_stage3_spawns`, `get_stage4_spawns`
- `get_spawns_for_stage`
- Helper functions (`_faction_stats`, `_faction_count`, `_split_count`, `_generate_scattered_positions`)

**Update `callbacks.py`** — add the import and class at the end.

### Step 4: Update all imports

Grep the entire `macro-brain/` for imports referencing moved items and update them:
```bash
grep -rn "from.*game_profile import\|from.*swarm_env import\|from.*curriculum import" macro-brain/src macro-brain/tests
```

### Step 5: Verify

```bash
cd macro-brain && source venv/bin/activate
python -m pytest tests/ -v --ignore=tests/test_terrain_generator.py
```

All tests must pass. Zero import errors.

## Verification_Strategy
  Test_Type: unit
  Test_Stack: Python (pytest)
  Acceptance_Criteria:
    - "game_profile.py under 200 lines"
    - "definitions.py contains all 19 dataclasses"
    - "swarm_env.py under 350 lines"
    - "curriculum.py under 300 lines"
    - "CurriculumCallback lives in callbacks.py"
    - "All existing Python tests pass"
    - "Zero import errors"
  Suggested_Test_Commands:
    - "cd macro-brain && source venv/bin/activate && python -m pytest tests/ -v --ignore=tests/test_terrain_generator.py"
