# Changelog - Task 07: Curriculum Stages

## Touched Files
- `macro-brain/src/training/curriculum.py` (Modified/Replaced)

## Contract Fulfillment
- Implemented `StageMapConfig` and `STAGE_MAP_CONFIGS` dataclass and global state containing config mapping.
- Added `get_map_config(stage: int)` helper.
- Implemented `get_spawns_for_stage` dispatch logic.
- Implemented 8 separate spawn generators corresponding to each curriculum stage, accurately instantiating faction ids, counts and starting coordinates using scaled world calculations or specified edge indices.
- Implemented `generate_terrain_for_stage` along with 4 specific map generation internal helpers matching the requested configurations.
- Updated module-level `ACTION_NAMES` with the new 8-action vocabulary.

## Deviations/Notes
- I substituted basic random number generation for stages 2 and 8 since python's built-in `random.choice` is easier to fall back to when the explicit `rng` generator is absent.
