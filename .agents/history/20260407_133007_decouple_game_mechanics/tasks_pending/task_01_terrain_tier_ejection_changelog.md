# Task 01: Terrain Tier Ejection — Changelog

## Touched Files
- `micro-core/src/terrain.rs` — MODIFIED

## Contract Fulfillment
- Removed `TERRAIN_DESTRUCTIBLE_MIN`, `TERRAIN_DESTRUCTIBLE_MAX`, `TERRAIN_PERMANENT_WALL` constants
- Added `impassable_threshold: u16` and `destructible_min: u16` fields to `TerrainGrid`
- Added `#[serde(default)]` annotations for backward-compatible deserialization
- Updated `is_destructible()`, `is_permanent_wall()`, `is_wall()`, `damage_cell()` to use instance fields
- Updated `TerrainGrid::new()` defaults: `impassable_threshold: u16::MAX`, `destructible_min: 0`
- Tests: `test_tier_constants_correct_order` → `test_tier_thresholds_injectable`, added `test_destructible_disabled_by_default` equivalent logic

## Deviations/Notes
- `systems.rs:380` struct literal already had the new fields included (from a prior edit session), so no scope violation occurred.
- The only remaining compile error (`wave_spawn_system` in `main.rs`) is from Task 02's removal, expected to be resolved by Task 03.

## Human Interventions
None.
