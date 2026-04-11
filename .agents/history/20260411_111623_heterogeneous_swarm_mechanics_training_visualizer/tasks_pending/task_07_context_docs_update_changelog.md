# Task 07: Context Documentation Update - Changelog

## Touched Files
- `.agents/context/engine-mechanics.md`
- `.agents/context/ipc-protocol.md`

## Contract Fulfillment
- Added "Unit Classes" section to `engine-mechanics.md`.
- Documented "Dynamic Range", "Stat-Driven Mitigation", "Interaction Cooldowns" and an "Example: Heterogeneous Combat" to `engine-mechanics.md`.
- Expanded `ipc-protocol.md` to document the new `SpawnConfig` with `unit_class_id`.
- Documented `CombatRulePayload` with new optional fields (`source_class`, `target_class`, `range_stat_index`, `mitigation`, `cooldown_ticks`) and documented `MitigationPayload` in `ipc-protocol.md`.

## Deviations/Notes
- The sections were successfully placed according to the surrounding context headers to ensure continuity.
