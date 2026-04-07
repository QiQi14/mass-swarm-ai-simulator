# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Contextless Audit + Debug Visualizer Contract
**Archived:** 2026-04-07
**Tasks Verified:** 7

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `directives_tests.rs` | task_a1_navigation_rules_payload | unit | rust | ** Tested NavigationRulePayload deserialization roundtrip.
- **Test Stack:** rust | PASS |
| `micro-core/src/rules/navigation.rs` | task_a2_nav_ruleset_default_empty | unit | rust/cargo test | ** Tested zero length for default navigation rules.
- **Test Stack:** rust/cargo test | PASS |
| `test_game_profile.py` | task_a3_python_nav_rules | unit | python (pytest) | ** Bidirectional default rules logic tests.
- **Test Stack:** python (pytest) | PASS |
| `micro-core/src/systems/spawning.rs` | task_a4_configurable_spawning | unit | rust/cargo test | ** Tested configurable initial stats and initial faction count defaults
- **Test Stack:** rust/cargo | PASS |
| `micro-core/src/config/simulation.rs` | task_a4_configurable_spawning | unit | rust/cargo test | ** Tested configurable initial stats and initial faction count defaults
- **Test Stack:** rust/cargo | PASS |
| `micro-core/src/systems/ws_command.rs` | task_b1_ws_rule_commands | unit | rust (cargo test) | ** Payload deserialization from generic JSON over MPSC channel into Bevy Resources.
- **Test Stack:* | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_a1_navigation_rules_payload | unit | 1 file(s) | PASS |
| task_a2_nav_ruleset_default_empty | unit | 1 file(s) | PASS |
| task_a3_python_nav_rules | unit | 1 file(s) | PASS |
| task_a4_configurable_spawning | unit | 2 file(s) | PASS |
| task_a5_remove_stat_fallback | unknown | manual only | PASS |
| task_b1_ws_rule_commands | unit | 1 file(s) | PASS |
| task_b2_debug_test_panel | manual_steps | manual only | FAIL |

---

*Generated on 2026-04-08 00:55:50*
