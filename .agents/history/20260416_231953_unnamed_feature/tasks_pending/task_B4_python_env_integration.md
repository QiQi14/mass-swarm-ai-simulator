# Task B4: Python Env Integration (Masking + Vectorizer)

- **Task_ID:** `B4_python_env_integration`
- **Execution_Phase:** 2 (Brain Phase B — depends on B1, B2 contracts)
- **Model_Tier:** `standard`
- **Live_System_Impact:** `destructive` — changes action mask shape + observation channels

## Target_Files
- `macro-brain/src/env/swarm_env.py` — MODIFY
- `macro-brain/src/utils/vectorizer.py` — MODIFY

## Dependencies
- B1 + B2 complete (Rust contracts for directive JSON + per-class density in snapshot)

## Context_Bindings
- `implementation_plan_brain_v3.md` — Contracts 3, 4 (snapshot JSON, mask shape)
- `strategy_brief.md` — §Per-Class Observation Channels, §Modifier masking per action type

## Strict_Instructions

### 1. Update swarm_env.py — 3D Action Masking

**action_masks() must return shape [8 + 2500 + 4] = [2512]:**

```python
def action_masks(self) -> np.ndarray:
    action_mask = np.zeros(NUM_ACTIONS, dtype=bool)
    coord_mask = np.ones(MAX_GRID_WIDTH * MAX_GRID_WIDTH, dtype=bool)
    modifier_mask = np.zeros(MODIFIER_DIM, dtype=bool)

    # Action dim masking (existing logic + new actions)
    action_mask[ACTION_HOLD] = True
    action_mask[ACTION_ATTACK_COORD] = True
    if self._curriculum_stage >= 2:
        action_mask[ACTION_ZONE_MODIFIER] = True
    if self._curriculum_stage >= 5:
        action_mask[ACTION_SPLIT_TO_COORD] = len(self._active_sub_factions) < 2
        action_mask[ACTION_MERGE_BACK] = len(self._active_sub_factions) > 0
        action_mask[ACTION_SET_PLAYSTYLE] = len(self._active_sub_factions) > 0
    if self._curriculum_stage >= 6:
        action_mask[ACTION_RETREAT] = True
    if self._curriculum_stage >= 7:
        action_mask[ACTION_ACTIVATE_SKILL] = True

    # Modifier dim: union of all valid modifiers for enabled actions
    for act_idx in range(NUM_ACTIONS):
        if action_mask[act_idx]:
            for m, allowed in enumerate(MODIFIER_MASKS[act_idx]):
                if allowed:
                    modifier_mask[m] = True

    return np.concatenate([action_mask, coord_mask, modifier_mask])
```

**Pass enemy_factions to multidiscrete_to_directives():**
```python
brain_directive, self._last_nav_directive = multidiscrete_to_directives(
    action, brain_faction=0,
    active_sub_factions=self._active_sub_factions,
    enemy_factions=self._enemy_factions,
)
```

### 2. Update vectorizer.py — Per-Class Density Channels (ch6, ch7)

Add new channels for class-specific density maps:

```python
# After existing channel processing, add:
class_density_maps = snapshot.get("class_density_maps", {})

# ch6: friendly class_0 density
if "0" in class_density_maps:
    ch6 = _reshape_and_pad(class_density_maps["0"], active_grid_h, active_grid_w)
else:
    ch6 = np.zeros((MAX_GRID_HEIGHT, MAX_GRID_WIDTH), dtype=np.float32)

# ch7: friendly class_1 density
if "1" in class_density_maps:
    ch7 = _reshape_and_pad(class_density_maps["1"], active_grid_h, active_grid_w)
else:
    ch7 = np.zeros((MAX_GRID_HEIGHT, MAX_GRID_WIDTH), dtype=np.float32)

result["ch6"] = ch6
result["ch7"] = ch7
```

**Update observation_channels count in the function signature/docs if it references a fixed number.**

### 3. Track enemy_factions in swarm_env

Ensure `self._enemy_factions` is populated during reset from spawn metadata:
```python
self._enemy_factions = list(meta.get("enemy_factions", []))
```

## Verification_Strategy
```
Test_Type: unit
Acceptance_Criteria:
  - "action_masks() returns array of shape [2512]"
  - "Modifier mask includes valid modifiers for enabled actions"
  - "ACTION_SET_PLAYSTYLE masked out when no active sub-factions"
  - "vectorize_snapshot populates ch6, ch7 from class_density_maps"
  - "Missing class_density_maps → ch6/ch7 are zero-filled"
Suggested_Test_Commands:
  - "cd macro-brain && .venv/bin/python -m pytest tests/test_vectorizer.py -v"
  - "cd macro-brain && .venv/bin/python -m pytest tests/ -v"
```
