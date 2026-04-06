# Task 09: Reward Shaping & Curriculum

**Task_ID:** `task_09_reward_shaping`
**Execution_Phase:** 5
**Model_Tier:** `standard`
**Target_Files:**
  - `macro-brain/src/env/rewards.py` (NEW)
  - `macro-brain/src/env/swarm_env.py` (MODIFY — wire `_compute_reward`)
  - `macro-brain/tests/test_rewards.py` (NEW)
**Dependencies:** Task 08 (training loop)
**Context_Bindings:**
  - `implementation_plan_feature_3.md` → Task 09 section (FULL — includes P5 patch)
  - `skills/rl_env_safety_patterns.md`

## Strict Instructions

See `implementation_plan_feature_3.md` → **Task 09: Reward Shaping** for full instructions.

**Summary:**
1. Create `rewards.py` with `flanking_bonus()` and `compute_shaped_reward()`
2. Wire `_compute_reward` in `swarm_env.py` to call `compute_shaped_reward`
3. 5 reward components: survival, kill, territory, health, flanking (weighted)

## CRITICAL: Pacifist Flank Exploit Fix (P5)
- Distance cutoff: sub-faction must be within `max_engage_radius` of enemy
- Distance attenuation: bonus decays linearly with distance
- Without this, RL agent parks sub-faction at map corner for free points

## Verification_Strategy
```
Test_Type: unit
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - P5: Distant sub-faction returns 0.0 flanking bonus
  - P5: Genuine close-range flank returns > 0.0
  - P5: Distance attenuation is monotonically decreasing
  - P5: No sub-faction density → 0.0 bonus
  - Shaped reward combines all 5 components correctly
Suggested_Test_Commands:
  - "cd macro-brain && python -m pytest tests/test_rewards.py -v"
```
