# Task 06: SwarmEnv Gymnasium Environment

**Task_ID:** `task_06_swarm_env`
**Execution_Phase:** 2
**Model_Tier:** `advanced`
**Target_Files:**
  - `macro-brain/src/env/swarm_env.py` (NEW)
  - `macro-brain/tests/test_swarm_env.py` (NEW)
**Dependencies:** Task 04 (Python scaffold — spaces.py, vectorizer.py)
**Context_Bindings:**
  - `implementation_plan_feature_3.md` → Task 06 section (FULL — includes patches P6, P7, P8)
  - `skills/rl_env_safety_patterns.md`

## Strict Instructions

See `implementation_plan_feature_3.md` → **Task 06: SwarmEnv Gymnasium Environment** for full instructions.

**Summary:**
1. Create `SwarmEnv(gym.Env)` with ZMQ REP socket (binds tcp://*:5555)
2. Implement `reset()` and `step(action)` with ZMQ recv→send alternation
3. Map Discrete(8) actions to MacroDirective JSON via `_action_to_directive()`
4. Implement `_get_density_centroid()` for dynamic epicenter (P6)

## CRITICAL: Three Mandatory Safety Patches
- **P6 DYNAMIC EPICENTER:** Calculate epicenter from density centroid, not hardcoded coordinates
- **P7 SINGLE SOURCE OF TRUTH:** Read `active_sub_factions` from Rust snapshot every step
- **P8 ZMQ + MDP:** Timeout → truncate episode; Tick swallowing loop for interventions

## ZMQ Protocol
- Python = REP (binds), Rust = REQ (connects)
- REP enforces strict recv → send alternation
- NEVER send before recv

## Verification_Strategy
```
Test_Type: unit
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - All 8 action types mapped to correct MacroDirective JSON
  - P6: Epicenter calculated from density centroid
  - P7: _active_sub_factions matches Rust snapshot
  - P8: ZMQ timeout truncates episode safely
  - P8: Intervention ticks swallowed
  - 13 tests total (8 action tests + 5 patch regression)
Suggested_Test_Commands:
  - "cd macro-brain && python -m pytest tests/test_swarm_env.py -v"
```
