# Changelog: Task 03 - Interaction System Upgrade

## Touched Files
* `micro-core/src/systems/interaction.rs`

## Contract Fulfillment
* Expanded `interaction_system` to include `UnitClassId` in the read-only query tuple, enabling fine-grained filtering of unit classes.
* Integrated `CooldownTracker` injection. The system now correctly ticks cooldowns at the start, skips logic when on cooldown, and starts cooldowns upon applying any target effect.
* Implemented class filtering logic for both source and target according to the `InteractionRule` configuration.
* Overhauled range lookup allowing dynamic resolution by indexing `source_entity` via `range_stat_index`.
* Implemented statutory `percent` and `flat` reduction mitigation mechanics.
* Updated standard existing tests with missing requirements (UnitClassId defaults, CooldownResource). Added comprehensive new tests for `test_mitigation_percent`, `test_mitigation_flat`, `test_cooldown_prevents_rapid_fire`, `test_dynamic_range`, and class filtering `test_class_filtering_source/target`.

## Deviations / Notes
* **Human Intervention Protocol - Flat Mitigation Formula Correction**: In `FlatReduction`, the brief instructions formula `abs_reduced = (base_delta.abs() - mit_value).max(0.0)` assumed `mit_value` was pre-scaled per frame. To align with the test condition ("Base damage = 10.0/sec. Verify effective damage = 5.0/sec. Target has stat[4] = 5.0."), I rectified the applied code to compute `let abs_reduced = (base_delta.abs() - mit_value * tick_delta).max(0.0);`. This ensures `mit_value` accurately acts as a per-second flat resistance mechanism.
* **Test Automation Note:** Passed all newly mandated 11 Unit Tests under `systems::interaction::tests`. One unrelated networking test (`test_ws_server_broadcast`) occasionally fails locally on `cargo test` explicitly due to `os error 48: Address already in use` (WS port 8080) caused by `./dev.sh --watch` running. This does not impact system integration.
