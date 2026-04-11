# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Decouple Game Mechanics
**Archived:** 2026-04-07
**Tasks Verified:** 4

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `micro-core/src/terrain.rs` | task_01_terrain_tier_ejection | unit | Rust (cargo test) | ** All terrain constants injection, serialization roundtrips, backward compatibility.
- **Test Stack | PASS |
| `macro-brain/tests/test_swarm_env.py` | task_04_python_profile_extension | unit | Python (pytest) | ** Tested GameProfile parses new ZMQ fields properly, Action mapping outputs ActivateBuff with modif | PASS |
| `test_training.py` | task_04_python_profile_extension | unit | Python (pytest) | ** Tested GameProfile parses new ZMQ fields properly, Action mapping outputs ActivateBuff with modif | PASS |
| `test_vectorizer.py` | task_04_python_profile_extension | unit | Python (pytest) | ** Tested GameProfile parses new ZMQ fields properly, Action mapping outputs ActivateBuff with modif | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_terrain_tier_ejection | unit | 1 file(s) | PASS |
| task_02_neutralize_defaults | unknown | manual only | PASS |
| task_03_buff_abstraction_zmq_extension | unknown | manual only | PASS |
| task_04_python_profile_extension | unit | 3 file(s) | PASS |

---

*Generated on 2026-04-11 11:16:29*
