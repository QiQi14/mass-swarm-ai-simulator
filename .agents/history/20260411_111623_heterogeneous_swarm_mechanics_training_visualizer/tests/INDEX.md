# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Heterogeneous Swarm Mechanics & Training Visualizer
**Archived:** 2026-04-11
**Tasks Verified:** 7

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `micro-core/src/components/unit_class.rs` | task_01_unit_class_component | unit | rust/cargo | ** UnitClassId implementation.
- **Test Stack:** rust/cargo | PASS |
| `micro-core/src/rules/interaction.rs` | task_02_interaction_rule_expansion | unit | cargo test (Rust) | ** Serialisation and deserialisation, empty cooldown functionality, backward compatibilities.
- **Te | PASS |
| `micro-core/src/config/cooldown.rs` | task_02_interaction_rule_expansion | unit | cargo test (Rust) | ** Serialisation and deserialisation, empty cooldown functionality, backward compatibilities.
- **Te | PASS |
| `micro-core/src/systems/interaction.rs` | task_03_interaction_system_upgrade | unit | cargo test (Rust) | ** Class filtering (source/target), dynamic range, mitigation (percent/flat), cooldown firing/preven | PASS |
| `micro-core/src/bridges/zmq_bridge/reset.rs` | task_04_spawn_reset_wiring | unit | cargo test (Rust) | ** Json mappings for new payload structs, environment reset wiring cooldown cleanup.
- **Test Stack: | PASS |
| `payloads.rs` | task_04_spawn_reset_wiring | unit | cargo test (Rust) | ** Json mappings for new payload structs, environment reset wiring cooldown cleanup.
- **Test Stack: | PASS |
| `tests/test_profile*.py` | task_05_python_profile_schema | unit | pytest (Python) | ** Python profile schema loading, backwards compatibility over dummy JSON and default arguments
- ** | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_unit_class_component | unit | 1 file(s) | PASS |
| task_02_interaction_rule_expansion | unit | 2 file(s) | PASS |
| task_03_interaction_system_upgrade | unit | 1 file(s) | PASS |
| task_04_spawn_reset_wiring | unit | 2 file(s) | PASS |
| task_05_python_profile_schema | unit | 1 file(s) | PASS |
| task_06_training_visualizer | unknown | manual only | PASS |
| task_07_context_docs_update | manual_steps | manual only | PASS |

---

*Generated on 2026-04-11 11:16:29*
