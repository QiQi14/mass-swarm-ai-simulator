# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** phase_2_universal_core_algorithms
**Archived:** 2026-04-04
**Tasks Verified:** 8

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `faction.rs` | task_01_context_agnostic_refactor | unit | unknown | ** Tests authored by executor cover:
  - `faction.rs`: display format, serde roundtrip (2 tests)
  - | PASS |
| `stat_block.rs` | task_01_context_agnostic_refactor | unit | unknown | ** Tests authored by executor cover:
  - `faction.rs`: display format, serde roundtrip (2 tests)
  - | PASS |
| `ws_sync.rs` | task_01_context_agnostic_refactor | unit | unknown | ** Tests authored by executor cover:
  - `faction.rs`: display format, serde roundtrip (2 tests)
  - | PASS |
| `ws_command.rs` | task_01_context_agnostic_refactor | unit | unknown | ** Tests authored by executor cover:
  - `faction.rs`: display format, serde roundtrip (2 tests)
  - | PASS |
| `zmq_protocol.rs` | task_01_context_agnostic_refactor | unit | unknown | ** Tests authored by executor cover:
  - `faction.rs`: display format, serde roundtrip (2 tests)
  - | PASS |
| `zmq_bridge/systems.rs` | task_01_context_agnostic_refactor | unit | unknown | ** Tests authored by executor cover:
  - `faction.rs`: display format, serde roundtrip (2 tests)
  - | PASS |
| `micro-core/src/spatial/hash_grid.rs` | task_02_spatial_hash_grid | unit | cargo test | ** All 8 unit tests passed
- **Test Stack:** cargo test | PASS |
| `micro-core/src/pathfinding/flow_field.rs` | task_03_flow_field_registry | unit | cargo test | ** All 9 unit tests passed
- **Test Stack:** cargo test | PASS |
| `micro-core/src/systems/interaction.rs` | task_05_interaction_removal_systems | unit | cargo test | ** All 8 unit tests passed (temporarily wired for execution context) 
- **Test Stack:** cargo test | PASS |
| `removal.rs` | task_05_interaction_removal_systems | unit | cargo test | ** All 8 unit tests passed (temporarily wired for execution context) 
- **Test Stack:** cargo test | PASS |
| `flow_field_update.rs` | task_06_flow_field_movement_spawning | unit | cargo test | ** All 11 unit tests passed successfully.
- **Test Stack:** cargo test | PASS |
| `micro-core/src/main.rs` | task_08_integration_stress_test | unit | cargo test, cargo run | ** Re-run of all global unit tests verified system integrity without regression parameters.
- **Test | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_context_agnostic_refactor | unit | 6 file(s) | PASS |
| task_02_spatial_hash_grid | unit | 1 file(s) | PASS |
| task_03_flow_field_registry | unit | 1 file(s) | PASS |
| task_04_rule_resources | unknown | manual only | PASS |
| task_05_interaction_removal_systems | unit | 2 file(s) | PASS |
| task_06_flow_field_movement_spawning | unit | 1 file(s) | PASS |
| task_07_ipc_visualizer_upgrades | unknown | manual only | FAIL |
| task_08_integration_stress_test | unit | 1 file(s) | PASS |

---

*Generated on 2026-04-08 00:55:50*
