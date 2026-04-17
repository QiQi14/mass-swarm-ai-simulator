# Task R01 Changelog: Rust WS Enhancements

## Touched Files
- `micro-core/src/systems/ws_command.rs` [MODIFIED]

## Contract Fulfillment
- **R01 spawn_wave Enhancement:** 
  - Handled parsing optional `class_id`, `movement`, and `engagement_range` fields from WS payload.
  - `spawn_wave` correctly sets up entities with custom definitions while defaulting to standard behavior if fields are missing (backward compatibility).
- **R02 set_interaction Enhancement:**
  - Transitioned from manual parsing of limited fields to proper fallback and exhaustive processing using `serde_json::from_value::<crate::rules::InteractionRule>` to support all filtering criteria (`source_class`, `target_class`, `cooldown_ticks`, etc.) seamlessly.
- **Testing:** Implemented comprehensive unit tests verifying the fallback mechanics and properly initialized fields for `spawn_wave` and `set_interaction`. Tested via `cargo test` and `cargo build` which passed successfully without new errors.

## Deviations / Notes
- No deviations from the Task Brief.
- Adhered rigidly to backward compat expectations. New payload schemas are verified compatible via serde defaults.
- All unit tests were appended inside existing test module.
