# Task 11: WS Protocol & Command Upgrade (Phase 3)

**Task_ID:** `task_11_ws_protocol_phase3`
**Execution_Phase:** 1 (parallel — after T02 within Phase 1)
**Model_Tier:** `standard`
**Target_Files:**
  - `micro-core/src/bridges/ws_protocol.rs` (MODIFY)
  - `micro-core/src/systems/ws_sync.rs` (MODIFY)
  - `micro-core/src/systems/ws_command.rs` (MODIFY)
**Dependencies:** Task 02 (Phase 3 resource types)
**Context_Bindings:**
  - `implementation_plan_feature_5.md` → Task 11 section
  - `skills/rust-code-standards`

## Strict Instructions

See `implementation_plan_feature_5.md` → **Task 11: WS Protocol & Command Upgrade** for full instructions.

**Summary:**

### Part A: Extend WS Broadcast
1. Add `ZoneModifierSync`, `MlBrainSync`, `AggroMaskSync` structs to `ws_protocol.rs` (behind `#[cfg(feature = "debug-telemetry")]`)
2. Extend `SyncDelta` with: `zone_modifiers`, `active_sub_factions`, `aggro_masks`, `ml_brain`, `density_heatmap`
3. Populate new fields in `ws_sync_system` (every 6 ticks for bandwidth control)

### Part B: New WS Commands
Add 7 commands to `ws_command_system`:
1. `place_zone_modifier` — write to `ActiveZoneModifiers`
2. `split_faction` — inject into `LatestDirective`
3. `merge_faction` — inject into `LatestDirective`
4. `set_aggro_mask` — write to `AggroMaskRegistry`
5. `inject_directive` — raw `MacroDirective` injection
6. `set_engine_override` — insert `EngineOverride` component
7. `clear_engine_override` — remove `EngineOverride` component

**Note:** T11 only needs resource TYPES from T02 (data-only structs). Resources will be empty until T05 populates them, but commands/broadcast are fully functional.

## Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - SyncDelta includes all new fields when debug-telemetry enabled
  - All 7 new WS commands are functional
  - place_zone_modifier adds to ActiveZoneModifiers
  - split_faction / merge_faction inject into LatestDirective
  - Existing WS commands still work (backward compatible)
Suggested_Test_Commands:
  - "cd micro-core && cargo test ws_command"
  - "cd micro-core && cargo test ws_sync"
```
