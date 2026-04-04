# Changelog: task_02_ecs_components

## Touched Files
- `micro-core/src/components/position.rs` [NEW]
- `micro-core/src/components/velocity.rs` [NEW]
- `micro-core/src/components/team.rs` [NEW]
- `micro-core/src/components/entity_id.rs` [NEW]
- `micro-core/src/components/mod.rs` [MODIFY]
- `micro-core/src/systems/spawning.rs` [MODIFY] (Fix for test compile errors)

## Contract Fulfillment
- `Position`: Component with `x: f32, y: f32`, supports JSON serialization.
- `Velocity`: Component with `dx: f32, dy: f32`, supports JSON serialization.
- `Team`: Enum with `Swarm` and `Defender`. Serializes to lowercase strings (`"swarm"`, `"defender"`).
- `EntityId`: Component with `id: u32`.
- `NextEntityId`: Resource starting at 1.
- `mod.rs`: Successfully re-exports all components and resources.

## Deviations/Notes
- **Standards Applied:** Applied `rust-code-standards` (module-level `//!` docs, `Ownership` metadata, and `AAA` testing patterns) to all new files.
- **Lowercase Serde:** Added `#[serde(rename_all = "lowercase")]` to `Team` to ensure IPC compliance as per `conventions.md`.
- **Epsilon checks:** Used `f32::EPSILON` for floating point comparisons in unit tests.
- **Build Fix:** Modified `micro-core/src/systems/spawning.rs` tests. The existing code was using `.query()` on an immutable `World` reference, which is invalid in Bevy 0.18. Fixed to use `app.world_mut().query()`. This was necessary to pass the `Acceptance_Criteria` of a successful `cargo build`.
