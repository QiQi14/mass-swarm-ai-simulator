# Test Archive Index

> Auto-generated. Run `python3 .agents/scripts/gen_tests_index.py <archive_path>` to regenerate.

**Feature:** Phase 3: Multi-Master Arbitration & RL Training
**Archived:** 2026-04-06
**Tasks Verified:** 11

## Test Files

| Test File | Task | Test Type | Test Stack | Criteria Covered | Result |
|-----------|------|-----------|------------|-----------------|--------|
| `micro-core/src/bridges/zmq_protocol.rs` | task_01_macro_directive_protocol | unit | unknown | **
  - AC1: 8 MacroDirective serde roundtrip tests (Hold, UpdateNavigation, TriggerFrenzy, Retreat,  | PASS |
| `micro-core/src/components/engine_override.rs` | task_02_phase3_resources | unit | unknown | **
  - AC1: `test_engine_override_default_no_ticks` → EngineOverride compiles with Vec2 and Option<u | PASS |
| `micro-core/src/config.rs` | task_02_phase3_resources | unit | unknown | **
  - AC1: `test_engine_override_default_no_ticks` → EngineOverride compiles with Vec2 and Option<u | PASS |
| `micro-core/src/systems/directive_executor.rs` | task_02_phase3_resources | unit | unknown | **
  - AC1: `test_engine_override_default_no_ticks` → EngineOverride compiles with Vec2 and Option<u | PASS |
| `micro-core/src/systems/state_vectorizer.rs` | task_03_state_vectorizer | unit | unknown | **
  - AC1 (dimensions): `test_density_map_single_entity` verifies map.len() == 100 for 10×10 grid
  | PASS |
| `macro-brain/tests/test_vectorizer.py` | task_04_python_scaffold | unit | unknown | **
  - AC1 (imports): `test_imports`
  - AC2 (obs space shape): `test_observation_space_shape` — ver | PASS |
| `micro-core/src/systems/directive_executor.rs` | task_05_directive_executor | unit | cargo test (Rust) | **
  - AC1 (8 directives): Hold, UpdateNavigation, TriggerFrenzy, Retreat, SetZoneModifier, SplitFac | PASS |
| `micro-core/src/systems/engine_override.rs` | task_05_directive_executor | unit | cargo test (Rust) | **
  - AC1 (8 directives): Hold, UpdateNavigation, TriggerFrenzy, Retreat, SetZoneModifier, SplitFac | PASS |
| `macro-brain/tests/test_swarm_env.py` | task_06_swarm_env | unit | pytest (Python) | **
  - AC1: 9 action mapping tests (Hold, UpdateNav, Frenzy, Retreat, ZoneModifier, SplitFaction, Me | PASS |
| `micro-core/src/bridges/zmq_bridge/systems.rs` | task_07_zmq_protocol_upgrade | unit | unknown | **
  - AC1-AC4: AiResponse parsing with all 8 MacroDirective variants + ResetEnvironment + legacy fa | PASS |
| `micro-core/src/systems/flow_field_update.rs` | task_07_zmq_protocol_upgrade | unit | unknown | **
  - AC1-AC4: AiResponse parsing with all 8 MacroDirective variants + ResetEnvironment + legacy fa | PASS |
| `macro-brain/tests/test_terrain_generator.py` | task_08_ppo_training | unit | unknown | **
  - AC1: terrain dimensions ← `test_terrain_generator_dimensions`
  - AC2: spawn zones clear ← `t | PASS |
| `macro-brain/tests/test_training.py` | task_08_ppo_training | unit | unknown | **
  - AC1: terrain dimensions ← `test_terrain_generator_dimensions`
  - AC2: spawn zones clear ← `t | PASS |
| `macro-brain/tests/test_rewards.py` | task_09_reward_shaping | unit | unknown | **
  - AC1: P5 distant sub-faction returns 0.0 ← `test_patch5_pacifist_flank_exploit_blocked`
  - AC | PASS |

## Verification Summary

| Task | Test Type | Files | Result |
|------|-----------|-------|--------|
| task_01_macro_directive_protocol | unit | 1 file(s) | PASS |
| task_02_phase3_resources | unit | 3 file(s) | PASS |
| task_03_state_vectorizer | unit | 1 file(s) | PASS |
| task_04_python_scaffold | unit | 1 file(s) | PASS |
| task_05_directive_executor | unit | 2 file(s) | PASS |
| task_06_swarm_env | unit | 1 file(s) | PASS |
| task_07_zmq_protocol_upgrade | unit | 2 file(s) | PASS |
| task_08_ppo_training | unit | 2 file(s) | PASS |
| task_09_reward_shaping | unit | 1 file(s) | PASS |
| task_11_ws_protocol_phase3 | unknown | manual only | PASS |
| task_12_visualizer_phase3 | manual | manual only | PASS |

---

*Generated on 2026-04-11 11:16:29*
