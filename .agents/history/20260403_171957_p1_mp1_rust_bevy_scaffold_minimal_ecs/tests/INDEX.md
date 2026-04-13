# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** P1-MP1 Rust/Bevy Scaffold + Minimal ECS
**Archived:** 2026-04-03
**Tasks Verified:** 4

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `main.rs` | task_01_project_scaffold | unit | cargo (Rust toolchain) | ** Verified project structure, module syntax, and `main.rs` compilation.
- **Test Stack:** `cargo (R | PASS |
| `position.rs` | task_02_ecs_components | unit | Rust (cargo test) | ** Serializations roundtrip, default value generations, and label stringifications.
- **Test Stack:* | PASS |
| `velocity.rs` | task_02_ecs_components | unit | Rust (cargo test) | ** Serializations roundtrip, default value generations, and label stringifications.
- **Test Stack:* | PASS |
| `team.rs` | task_02_ecs_components | unit | Rust (cargo test) | ** Serializations roundtrip, default value generations, and label stringifications.
- **Test Stack:* | PASS |
| `entity_id.rs` | task_02_ecs_components | unit | Rust (cargo test) | ** Serializations roundtrip, default value generations, and label stringifications.
- **Test Stack:* | PASS |
| `micro-core/src/systems/movement.rs` | task_03_systems_config | unit | Rust (cargo test) | ** All Acceptance Criteria have mapping to the written tests.
- **Test Stack:** Rust (cargo test) | PASS |
| `micro-core/src/systems/spawning.rs` | task_03_systems_config | unit | Rust (cargo test) | ** All Acceptance Criteria have mapping to the written tests.
- **Test Stack:** Rust (cargo test) | PASS |
| `micro-core/src/systems/mod.rs` | task_03_systems_config | unit | Rust (cargo test) | ** All Acceptance Criteria have mapping to the written tests.
- **Test Stack:** Rust (cargo test) | PASS |
| `micro-core/src/config.rs` | task_03_systems_config | unit | Rust (cargo test) | ** All Acceptance Criteria have mapping to the written tests.
- **Test Stack:** Rust (cargo test) | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_project_scaffold | unit | 1 file(s) | PASS |
| task_02_ecs_components | unit | 4 file(s) | PASS |
| task_03_systems_config | unit | 4 file(s) | PASS |
| task_04_integration_smoke | unknown | manual only | PASS |

---

*Generated on 2026-04-11 11:16:29*
