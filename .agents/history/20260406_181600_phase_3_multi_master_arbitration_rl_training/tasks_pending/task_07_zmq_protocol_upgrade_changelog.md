# Task 07: ZMQ Protocol Upgrade — Changelog

## Summary

Extended the ZMQ AI bridge to support the full Multi-Master Arbitration protocol.
The `StateSnapshot` now exports density maps, zone modifiers, aggro masks, intervention
flags, and active sub-factions. The `ai_poll_system` parses `AiResponse` discriminated
unions (supporting both `MacroDirective` and `ResetEnvironment` responses) with legacy
`MacroAction` fallback. The `flow_field_update_system` handles `NavigationTarget::Waypoint`
and enforces the Moses Effect Guard for zone modifier overlays.

## Files Modified

### `micro-core/src/bridges/zmq_bridge/systems.rs`
- **MODIFIED**: `build_state_snapshot()` — Added parameters for `ActiveZoneModifiers`,
  `InterventionTracker`, `ActiveSubFactions`, `AggroMaskRegistry`. Populates
  `density_maps` (raw HashMap via `state_vectorizer::build_density_maps`),
  `active_zones` (Vec<ZoneModifierSnapshot>), `aggro_masks` (HashMap<String, bool>),
  `intervention_active`, and `active_sub_factions`.
- **MODIFIED**: `ai_trigger_system()` — Passes new resource parameters to
  `build_state_snapshot()`.
- **MODIFIED**: `ai_poll_system()` — Parses `AiResponse` discriminated union
  (supports `macroDirective` + `reset_environment`). Legacy `MacroAction` fallback
  maps to `Hold`. Stores parsed directive in `LatestDirective` for executor.
- **ADDED**: 12 unit tests covering snapshot fields, directive parsing, and legacy fallback.

### `micro-core/src/bridges/zmq_bridge/mod.rs`
- **MODIFIED**: Added `LatestDirective` resource registration in `ZmqBridgePlugin::build()`.
  Updated ownership comment to task_07.

### `micro-core/src/systems/flow_field_update.rs`
- **MODIFIED**: `flow_field_update_system()` — Added `NavigationTarget::Waypoint` handling
  with static goal coordinates (no fog filtering). Waypoint flow fields stored under
  key `follower_faction + 100_000` to avoid collision with faction IDs.
- **ADDED**: `apply_zone_overlays()` — Extracted zone modifier cost overlay logic with
  **PATCH 2: MOSES EFFECT GUARD** (wall tiles `u16::MAX` are immune to cost modifiers).
- **ADDED**: 4 unit tests: `test_flow_field_waypoint_target`,
  `test_flow_field_zone_modifier_wall_immune`, `test_flow_field_zone_modifier_attract`,
  `test_flow_field_zone_modifier_repel`.

## Safety Patches Implemented

| # | Patch | Location | Verification |
|---|-------|----------|--------------|
| P2 | **Moses Effect Guard** | `apply_zone_overlays()` | `test_flow_field_zone_modifier_wall_immune` |
| P1 | **Vaporization Guard** | `LatestDirective.take()` (in directive_executor.rs — consumed via Task 05) | Verified by existing `test_vaporization_guard_*` tests |

## Test Results

```
cargo test                  → 169 passed, 0 failed
cargo test zmq              →  30 passed, 0 failed
cargo test flow_field       →  24 passed, 0 failed
cargo test state_vectorizer →  10 passed, 0 failed
```

## Human Interventions

None.
