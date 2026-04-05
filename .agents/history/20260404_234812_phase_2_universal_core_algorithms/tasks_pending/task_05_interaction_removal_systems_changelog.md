# Task 05 Changelog: Interaction & Removal Systems

## Touched Files
- `micro-core/src/systems/interaction.rs` (Created)
- `micro-core/src/systems/removal.rs` (Created)

## Contract Fulfillment
- Implemented `interaction_system` utilizing Zero-Allocation Disjoint Queries (`q_ro` and `q_rw`), avoiding monolithic collect/apply overhead as specified.
- Implemented `removal_system` which utilizes deferred despawns via Bevy `Commands` and records despawned entity IDs into `RemovalEvents`.
- Enforced single-threaded fixed-tick execution (`delta: 1.0/60.0`), avoided `par_iter()`.
- Implemented all 4 required unit tests for Interaction and 4 required unit tests for Removal within the respective files.

## Deviations/Notes
- Per the instructions, `micro-core/src/systems/mod.rs` was NOT modified. Task 08 is responsible for wiring these modules.
- Due to the new files not being wired into `mod.rs`, their local `#[cfg(test)]` unit tests are currently untrackable by `cargo test`.
- A background `cargo test` run discovered missing fields in `SimulationConfig` instantiation inside `movement.rs` and `spawning.rs`, likely pending other parallel task updates. I have purposely left these unmodified to strictly adhere to the `Target_Files` scope.
- Stats are expressly NOT clamped logic-wise (negatives permitted for "Overkill Gradient" purposes) and the system validates bounds checking before resolving stat modifiers.
