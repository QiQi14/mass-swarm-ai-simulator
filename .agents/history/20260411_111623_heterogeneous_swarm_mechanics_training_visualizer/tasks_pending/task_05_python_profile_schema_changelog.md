# Task 05: Python Profile Schema Update

## Touched Files
- `macro-brain/src/config/definitions.py`
- `macro-brain/src/config/parser.py`
- `macro-brain/src/config/game_profile.py`

## Contract Fulfillment
- Added `UnitClassConfig` and `MitigationConfig` to schema definitions (`definitions.py`).
- Expanded `CombatRuleConfig` with optional `source_class`, `target_class`, `range_stat_index`, `mitigation`, and `cooldown_ticks`, defaulting to `None`.
- Updated `parser.py` to optionally parse `unit_registry` matching the schema and incorporated the inner `_parse_combat_rule` logic to handle fetching the optional/nested dictionary for configuration values (falling back gracefully for backward compatibility).
- Added `unit_registry` to `GameProfile`.
- Updated `game_profile.py` to add `_build_spawn_config` and `_build_combat_rule` helper routines, invoking the latter during combat payload serialize operations (`combat_rules_payload`).

## Deviations/Notes
- `unit_registry` was explicitly added as a new configurable parameter on the actual `GameProfile` dataclass object (since it needs to be stored).
- `_parse_unit_registry` and `_parse_combat_rule` were implemented as inner closure routines inside `_parse_profile` to maintain the existing module-level schema consistency.
- `_build_spawn_config` was added to `GameProfile` per instructions, although spawns are currently explicitly defined inside `training/curriculum.py`. The interface acts as a formal helper payload builder for any external callers or future pipeline transitions.
