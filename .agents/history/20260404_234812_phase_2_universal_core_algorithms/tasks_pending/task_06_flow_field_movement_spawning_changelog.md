# Task 06 Changelog: Flow Field + Movement + Spawning

## Touched Files
- **[NEW]** `micro-core/src/components/movement_config.rs`: Implemented `MovementConfig` component to define entity movement tuning (max speed, separation, steering factor, flow weight).
- **[MODIFY]** `micro-core/src/components/mod.rs`: Re-exported `MovementConfig` component.
- **[MODIFY]** `micro-core/src/config.rs`: Expanded `SimulationConfig` with flow field update interval and wave spawn data parameters.
- **[MODIFY]** `micro-core/src/systems/movement.rs`: Rewrote system to use `par_iter_mut()` for multi-threaded multi-agent composite steering. Added Boids zero-sqrt inverse-linear separation using the closure `for_each_in_radius()`, and incorporated boundary clamping. Added five unit tests.
- **[NEW]** `micro-core/src/systems/flow_field_update.rs`: Implemented the flow field recalculation system processing at `config.flow_field_update_interval`. Automatically cleans up unused flow fields. Added unit tests.
- **[MODIFY]** `micro-core/src/systems/spawning.rs`: Added the new `wave_spawn_system()` and adjusted `initial_spawn_system()` so that if `FactionId` equals `config.wave_spawn_faction`, the `MovementConfig` component is inserted as well. Included missing tests.

## Contract Fulfillment
- All requested movement behaviors—Composite Steering, Inverse-Linear zero-sqrt separation, multi-threaded `par_iter_mut()`, and `TickCounter` references—were implemented per Contract 7 & 9.
- Boundary clamping relies strictly on `.clamp(0.0, world_width/height)` to avoid toroidal-wrapping overlaps in paths.
- `Velocity { dx, dy }` architecture was preserved strictly.

## Deviations/Notes
- `bevy::platform::collections::HashMap` was used instead of `bevy::utils::HashMap` to align with the framework's available import paths.
- Used `entity.to_bits()` instead of `entity.index()` modulo math since `EntityIndex` cannot directly compute remainders. 
- `micro-core/src/systems/flow_field_update.rs` was added but intentionally NOT exported inside `systems/mod.rs` to strictly obey the instruction "*DO NOT modify systems/mod.rs — Task 08 handles wiring.*". As a result, its tests will be compiled and validated once Task 08 is finished.

## Human Interventions
No human interventions took place during this execution attempt.
