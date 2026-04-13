# QA Certification Report: task_06_swarm_env

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | 2026-04-06 | PASS | All 8 actions mapped correctly. 3 safety patches verified via 16 tests. No scope violations. |

---

## Latest Verification (Attempt 1)

### 1. Build Gate
- **Command:** `cd macro-brain && PYTHONPATH=. python -c "from src.env.swarm_env import SwarmEnv; print('Import OK')"`
- **Result:** PASS — module imports successfully
- **Evidence:**
```
Import OK
```

### 2. Regression Scan
- **Prior Tests Found:** `macro-brain/tests/test_spaces.py`, `macro-brain/tests/test_vectorizer.py` from Task 04
- **Reused/Adapted:** Task 04 tests confirmed passing; Task 06 tests build on the same spaces/vectorizer modules

### 3. Test Authoring
- **Test Files Created:** `macro-brain/tests/test_swarm_env.py` (16 tests)
- **Coverage:**
  - AC1: 9 action mapping tests (Hold, UpdateNav, Frenzy, Retreat, ZoneModifier, SplitFaction, MergeFaction×2, AggroMask)
  - AC2 (P6): `test_patch6_dynamic_epicenter_uses_centroid`, `test_density_centroid_empty_map`, `test_density_centroid_concentration`
  - AC3 (P7): `test_patch7_sub_factions_from_snapshot`, `test_patch7_split_id_from_ground_truth`
  - AC4 (P8): `test_patch8_intervention_swallowing`, `test_patch8_zmq_timeout_truncates`
- **Test Stack:** pytest (Python)

### 4. Test Execution Gate
- **Commands Run:** `cd macro-brain && PYTHONPATH=. python -m pytest tests/test_swarm_env.py -v`
- **Results:** 16 passed, 0 failed, 0 skipped
- **Evidence:**
```
tests/test_swarm_env.py::test_action_to_directive_hold PASSED            [  6%]
tests/test_swarm_env.py::test_action_to_directive_update_nav PASSED      [ 12%]
tests/test_swarm_env.py::test_action_to_directive_frenzy PASSED          [ 18%]
tests/test_swarm_env.py::test_action_to_directive_retreat PASSED         [ 25%]
tests/test_swarm_env.py::test_action_to_directive_zone_modifier PASSED   [ 31%]
tests/test_swarm_env.py::test_action_to_directive_split_faction PASSED   [ 37%]
tests/test_swarm_env.py::test_action_to_directive_merge_faction_no_sub PASSED [ 43%]
tests/test_swarm_env.py::test_action_to_directive_merge_faction_with_sub PASSED [ 50%]
tests/test_swarm_env.py::test_action_to_directive_aggro_mask_toggle PASSED [ 56%]
tests/test_swarm_env.py::test_patch6_dynamic_epicenter_uses_centroid PASSED [ 62%]
tests/test_swarm_env.py::test_patch7_sub_factions_from_snapshot PASSED   [ 68%]
tests/test_swarm_env.py::test_patch7_split_id_from_ground_truth PASSED   [ 75%]
tests/test_swarm_env.py::test_density_centroid_empty_map PASSED          [ 81%]
tests/test_swarm_env.py::test_density_centroid_concentration PASSED      [ 87%]
tests/test_swarm_env.py::test_patch8_intervention_swallowing PASSED      [ 93%]
tests/test_swarm_env.py::test_patch8_zmq_timeout_truncates PASSED       [100%]
============================== 16 passed in 0.15s ==============================
```

### 5. Acceptance Criteria
| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | All 8 action types mapped to correct MacroDirective JSON | ✅ | 9 action-mapping tests pass (MergeFaction has 2 variants: with/without sub-factions) |
| 2 | P6: Epicenter calculated from density centroid | ✅ | `test_patch6_dynamic_epicenter_uses_centroid` — verifies centroid computation from density map |
| 3 | P7: _active_sub_factions matches Rust snapshot | ✅ | `test_patch7_sub_factions_from_snapshot` — reads from snapshot `active_sub_factions` |
| 4 | P8: ZMQ timeout truncates episode safely | ✅ | `test_patch8_zmq_timeout_truncates` — raises zmq.Again, returns truncated=True |
| 5 | P8: Intervention ticks swallowed | ✅ | `test_patch8_intervention_swallowing` — loops past intervention_active=True ticks |

### 6. Negative Path Testing
| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| Empty density map | Falls back to world center | `_get_density_centroid` returns (500, 500) | ✅ |
| No active sub-factions for MergeFaction | Falls back to Hold | `_action_to_directive` returns Hold | ✅ |
| No active sub-factions for AggroMask | Falls back to Hold | Returns Hold | ✅ |
| ZMQ timeout during reset | Sample observation returned | `reset()` catches `zmq.Again`, reconnects, returns `.sample()` | ✅ |

### 7. Certification Decision
- **Status:** COMPLETE
- **Notes:**
  - **Module naming deviation:** Executor used `from src.env.*` instead of `from macro_brain.env.*` due to Python's invalid module name for hyphenated directories (`macro-brain`). This is documented in `.agents/knowledge/python/gotcha_hyphen_module_name.md` — correct approach.
  - **ZMQ protocol correctness:** REP socket correctly binds on `tcp://*:5555`. Strict `recv→send` alternation enforced in both `reset()` and `step()`.
  - **Code quality:** Clean separation of concerns. Safety patches are well-isolated and independently testable.
