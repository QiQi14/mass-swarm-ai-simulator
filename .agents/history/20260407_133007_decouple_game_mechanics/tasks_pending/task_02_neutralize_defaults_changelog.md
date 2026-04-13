# Changelog for Task 02: Neutralize Defaults

## Touched Files
- `micro-core/src/rules/interaction.rs`
- `micro-core/src/rules/removal.rs`
- `micro-core/src/components/movement_config.rs`
- `micro-core/src/systems/spawning.rs`
- `micro-core/src/systems/mod.rs`
- `micro-core/src/systems/movement.rs` (to fix tests failing on new `MovementConfig::default()`)
- `micro-core/src/bridges/zmq_bridge/systems.rs` (fixed `TerrainGrid` instantiation lacking `destructible_min`/`impassable_threshold` to keep tests compiling)

## Contract Fulfillment
- Neutralized `InteractionRuleSet::default()` and updated corresponding tests.
- Neutralized `RemovalRuleSet::default()` and updated corresponding tests.
- Neutralized `MovementConfig::default()` by zeroing configurations.
- Removed `wave_spawn_system` and tests from `spawning.rs` and `mod.rs`.

## Deviations/Notes
- Updated tests in `movement.rs` which implicitly relied on movement config values provided by `MovementConfig::default()`. Supplied standard `MovementConfig` instances where necessary instead of relying on default.
- Supplied `destructible_min` and `impassable_threshold` fields directly inside `TerrainGrid` initialization during `reset_environment_system` inside `zmq_bridge/systems.rs` to fix `E0063` compiler errors as Task 01 injected new terrain thresholds to `TerrainGrid`.
