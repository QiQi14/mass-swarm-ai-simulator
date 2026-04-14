# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Unnamed Feature
**Archived:** 2026-04-08
**Tasks Verified:** 9

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `macro-brain/tests/test_bot_controller.py` | task_a1_bot_controller | unit | pytest | ** Covers all acceptance criteria: hysteresis logic, builders, faction counting, and fallback.
- **T | PASS |
| `macro-brain/tests/test_validator.py` | task_a2_profile_validator | unit | pytest | ** All 9 rules V1 to V9 mapped nicely to unit tests.
- **Test Stack:** pytest | PASS |
| `macro-brain/tests/test_run_manager.py` | task_a3_run_manager | unit | pytest | ** Directory path mapping, filesystem generation, timestamp uniqueness.
- **Test Stack:** pytest | PASS |
| `macro-brain/tests/test_bot_behavior.py` | task_b1_bot_config | unit | pytest | ** Maps conversion values, backwards compatibility testing, tick loop serialization checking mapped  | PASS |
| `macro-brain/tests/test_stage5_terrain.py` | task_b3_stage5_terrain | unit | pytest | ** Tested 100.0/900.0 boundaries mapping, brain logic random counts generated cleanly, and dictionar | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_a1_bot_controller | unit | 1 file(s) | PASS |
| task_a2_profile_validator | unit | 1 file(s) | PASS |
| task_a3_run_manager | unit | 1 file(s) | PASS |
| task_b1_bot_config | unit | 1 file(s) | PASS |
| task_b2_zmq_protocol | unknown | manual only | PASS |
| task_b3_stage5_terrain | unit | 1 file(s) | PASS |
| task_c1_train_preflight | manual_steps | manual only | PASS |
| task_c2_train_sh | manual_steps | manual only | PASS |
| task_c3_training_status | unknown | manual only | PASS |

---

*Generated on 2026-04-13 20:18:34*
