# Task 01: MacroDirective Protocol Changelog

## Touched Files
- `micro-core/src/bridges/zmq_protocol.rs` (MODIFIED): Added `MacroDirective` enum, `NavigationTarget` enum, new fields to `StateSnapshot`, and 12 unit tests.
- `micro-core/src/bridges/zmq_bridge/systems.rs` (MODIFIED): Added initializers for the new `StateSnapshot` fields to fix a compilation error (this was the reported GAP).

## Contract Fulfillment
- Ensured all 8 `MacroDirective` variants (`Hold`, `UpdateNavigation`, `TriggerFrenzy`, `Retreat`, `SetZoneModifier`, `SplitFaction`, `MergeFaction`, `SetAggroMask`) are present and serialize using `tag = "directive"`.
- Added `NavigationTarget` enum (serializes using `tag = "type"`).
- Extended `StateSnapshot` fields correctly.
- Added 12 unit tests which all pass `cargo test`.
- Included patches to resolve compilation in `systems.rs` unblocking future stages.

## Deviations/Notes
- Because `StateSnapshot` is statically constructed in `micro-core/src/bridges/zmq_bridge/systems.rs`, adding new fields to it in `zmq_protocol.rs` broke the build. We had to modify `systems.rs` to initialize these fields using `Default::default()`. This file was outside the `Target_Files` boundary defined in the task brief, causing an execution GAP.

## Human Interventions
- The user escalated the boundary violation (GAP) to the architect. The architect verified the fix in `systems.rs` and marked the task as completed to unblock the sequence. QA must accept this boundary-crossing modification as valid and necessary.
