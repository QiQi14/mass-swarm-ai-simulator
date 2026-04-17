# Changelog for Task B4: Python Env Integration

## Touched Files
- `macro-brain/src/env/swarm_env.py`
- `macro-brain/src/utils/vectorizer.py`

## Contract Fulfillment
- `action_masks()` has been updated to output a mask of shape `[8 + 2500 + 4]` = `[2512]`.
- Implemented modifier mask union for all enabled actions using `MODIFIER_MASKS`.
- Set action masks properly respecting stage unlocks.
- Modified `vectorizer.py` to extract `class_density_maps` and place `class_0` into `ch6` and `class_1` into `ch7`.
- Extracted `enemy_factions` from `role_meta` on `reset()` and passed it into `multidiscrete_to_directives` along with `active_sub_factions`.

## Deviations/Notes
- Removed the "Dynamic Count Normalization (ch0, ch1, ch6)" block from `vectorizer.py` per QA feedback, as it was unauthorized by the task contract and broke tests.
- Fixed two `AttributeError` instances in `swarm_env.py` caused by a typo in the original prompt (`_curriculum_stage`) and a missing initialization for `_enemy_factions`.
- For `vectorizer.py`, instead of replacing the entire channels list dictionary or building it from scratch on result dict, the existing `channels[6]` and `channels[7]` logic was replaced with `class_density_maps` as intended to match the existing padding architecture and numpy array setup.
- Used `make_coordinate_mask` from `src.env.spaces` inside `action_masks` instead of a plain array of ones to ensure only the valid coordinates are enabled, enforcing safety against out of bounds actions.

## Human Interventions
- None.
