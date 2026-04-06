# Task 07: ZMQ Protocol Upgrade

**Task_ID:** `task_07_zmq_protocol_upgrade`
**Execution_Phase:** 3
**Model_Tier:** `standard`
**Target_Files:**
  - `micro-core/src/bridges/zmq_bridge/systems.rs` (MODIFY)
  - `micro-core/src/bridges/zmq_protocol.rs` (MODIFY)
  - `micro-core/src/bridges/zmq_bridge/mod.rs` (MODIFY)
  - `micro-core/src/systems/flow_field_update.rs` (MODIFY)
**Dependencies:** Task 03 (DensityMaps), Task 05 (directive executor resources + systems)
**Context_Bindings:**
  - `implementation_plan_feature_2.md` → Task 07 section
  - `skills/rust-code-standards`

## Strict Instructions

See `implementation_plan_feature_2.md` → **Task 07: ZMQ Protocol Upgrade** for full instructions.

**Summary:**
1. Extend `StateSnapshot` to include `density_maps`, `intervention_active`, `active_zones`, `active_sub_factions`, `aggro_masks`
2. Upgrade ZMQ ai_poll_system to: populate density maps from `DensityMaps` resource, send extended snapshot, parse `MacroDirective` response (fallback to legacy `MacroAction`)
3. Apply zone modifier cost overlay in `flow_field_update_system` with **PATCH 2: MOSES EFFECT GUARD**
4. Migrate `NavigationRule` from `target_faction: u32` to `target: NavigationTarget`

## CRITICAL: Moses Effect Guard
Zone overlay MUST skip `u16::MAX` tiles: `if current_cost == u16::MAX { continue; }`

## Verification_Strategy
```
Test_Type: unit + integration
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - StateSnapshot includes all new fields
  - MacroDirective parsed correctly from JSON
  - Legacy MacroAction fallback works
  - Moses Effect: wall tiles immune to cost modifiers
  - Flow field zone overlay applies correctly to non-wall tiles
Suggested_Test_Commands:
  - "cd micro-core && cargo test zmq"
  - "cd micro-core && cargo test flow_field"
```
