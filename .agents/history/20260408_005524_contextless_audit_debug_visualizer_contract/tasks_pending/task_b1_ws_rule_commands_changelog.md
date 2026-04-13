# Changelog: task_b1_ws_rule_commands

## Touched Files
- `micro-core/src/systems/ws_command.rs`: Modified to add rule configuration commands over WebSocket and group arguments to respect ECS limits.

## Contract Fulfillment
- Handled `set_navigation` WS command and updated `NavigationRuleSet`.
- Handled `set_interaction` WS command and updated `InteractionRuleSet`.
- Handled `set_removal` WS command and updated `RemovalRuleSet`.

## Deviations / Notes
- Grouped `ResMut` variables (`rule_sets` and `optionals`) in `ws_command_system` as a tuple parameter to avoid exceeding Bevy's 16 system parameter limit. This resolved compilation issues after adding the three rule parameters.
- Updated `#[allow(clippy::type_complexity)]` on `ws_command_system` to resolve the related warning caused by the new grouped structures.
- Added `NavigationRuleSet`, `InteractionRuleSet`, and `RemovalRuleSet` resources to `setup_app()` in `tests` module for successful execution of unit tests.
- Re-verified test suite and clippy, returning a clear bill of health for `ws_command.rs`.

## Human Interventions
None.
