## Touched Files:
- `micro-core/src/bridges/zmq_protocol/payloads.rs`: Added `zone_modifier_duration_ticks` to `AbilityConfigPayload` with a custom `default_zone_duration` serde default.
- `micro-core/src/config/buff.rs`: Added `zone_modifier_duration_ticks` to `BuffConfig` and implemented manual `Default` (defaulting to 120 ticks).
- `micro-core/src/bridges/zmq_bridge/reset.rs`: Updated `reset_environment_system` to apply `cfg.zone_modifier_duration_ticks` when parsing reset payloads.
- `micro-core/src/systems/directive_executor/executor.rs`: Added `buff_config: Res<crate::config::BuffConfig>` parameter to `directive_executor_system` and used its value for `ticks_remaining` when creating `ZoneModifier` from `SetZoneModifier` directives.
- `micro-core/src/systems/directive_executor/executor_tests.rs`: Added `app.insert_resource(crate::config::BuffConfig::default());` to test environment `setup_app()`.
- `micro-core/src/bridges/zmq_bridge/systems.rs`: Added `app.insert_resource(crate::config::TrainingMode(false));` to test configs to fix an existing test panic.

## Contract Fulfillment:
- Updated `AbilityConfigPayload` to support configurable zone modifier duration.
- Handled backwards compatibility perfectly by injecting a method using serde defaults `default_zone_duration`.
- Connected configuration downstream into the ECS `BuffConfig`.
- Set zone duration appropriately in `directive_executor_system`.
- Preserved `executor_tests.rs` behavior and only augmented `setup_app()`.

## Deviations/Notes:
- `test_ws_server_broadcast` test may fail if port 8080 is locally in-use by `dev.sh --watch` process, but it is entirely out of scope for this task regarding `zone duration` mechanics.
- Fixed two unrelated, existing failures in the `bridges::zmq_bridge::systems` tests failing due to an uninitialized `TrainingMode` resource during app testing to make `cargo test` run cleaner. No other modifications were introduced.

## Human Interventions
- None.
