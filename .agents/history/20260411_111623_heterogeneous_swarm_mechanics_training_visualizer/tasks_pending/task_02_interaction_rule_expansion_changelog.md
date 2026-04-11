# Changelog for task_02_interaction_rule_expansion

## Touched Files:
- `micro-core/src/rules/interaction.rs`
- `micro-core/src/config/cooldown.rs` (created)
- `micro-core/src/config/mod.rs`
- `micro-core/src/systems/ws_command.rs`
- `micro-core/src/systems/interaction.rs`
- `micro-core/src/bridges/zmq_bridge/reset.rs`

## Contract Fulfillment:
- Added `MitigationRule` and `MitigationMode` definitions to `interaction.rs`.
- Expanded `InteractionRule` with new optional fields (`source_class`, `target_class`, `range_stat_index`, `mitigation`, `cooldown_ticks`).
- Implemented `CooldownTracker` resource in `config/cooldown.rs`.
- Exposed `cooldown` in `config/mod.rs`.
- Updated test suites and existing explicit `InteractionRule` initializations properly setting the new fields to `None`, to preserve backwards compatibility.

## Deviations/Notes:
- Due to the addition of fields to the `InteractionRule` struct which does not derive `Default`, I had to update multiple struct initializations referencing `InteractionRule` across `ws_command.rs`, `interaction.rs` and `reset.rs` to fix compile errors and explicitly set the new fields to `None`.
