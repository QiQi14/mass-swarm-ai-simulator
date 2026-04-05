## Touched Files
- `micro-core/src/visibility.rs` (Created)
- `micro-core/src/components/vision_radius.rs` (Created)
- `micro-core/src/components/mod.rs` (Modified)
- `micro-core/src/lib.rs` (Modified)

## Contract Fulfillment
- Implemented `VisionRadius` component wrapping `f32` with a default of 80.0.
- Implemented `FactionVisibility` bit-packed Resource holding `explored` and `visible` HashMaps.
- Included static helper methods for bit manipulation `bitpack_len`, `set_bit`, `get_bit`, `clear_all`.
- Implemented instance methods `new`, `ensure_faction`, `reset_explored`.
- Added required unit tests proving functionality, ensuring `cargo test visibility` passes successfully.

## Deviations/Notes
- Created `micro-core/src/components/vision_radius.rs` and updated `micro-core/src/components/mod.rs` instead of modifying a monolithic `components.rs` because `components` in the project is structured as a module directory. This was an architectural adaptation matching the underlying source structure.
- Used `std::collections::HashMap` instead of `bevy::platform::collections::HashMap` as requested in the brief, as the latter did not resolve in the Bevy root for the project workspace.

## Human Interventions
None.
