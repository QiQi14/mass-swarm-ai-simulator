# Task 04: Spawn & Reset Wiring Changelog

## Touched Files
- `micro-core/src/bridges/zmq_protocol/payloads.rs` [MODIFIED]
- `micro-core/src/bridges/zmq_bridge/reset.rs` [MODIFIED]

## Contract Fulfillment
- Extended `SpawnConfig` with `unit_class_id`.
- Extended `CombatRulePayload` to include `source_class`, `target_class`, `range_stat_index`, `mitigation`, and `cooldown_ticks`.
- Created `MitigationPayload` structure for combat rule deserialization.
- Updated the Spawn logic in `reset_environment_system` to map `unit_class_id` to its respective `UnitClassId` component.
- Updated Interaction mapping in `reset_environment_system` to handle newly added fields and pass configurations.
- Integrated `CooldownTracker` reset correctly within `reset_environment_system`.

## Deviations/Notes
- The namespace for `MitigationRule` and `MitigationMode` used within `reset_environment_system` is referenced as `crate::rules::interaction::MitigationRule` and `crate::rules::interaction::MitigationMode` since Task 02 did not explicitly export them into `crate::rules`. This maintains adherence to rules without touching out-of-scope files.

## Human Interventions
None.
