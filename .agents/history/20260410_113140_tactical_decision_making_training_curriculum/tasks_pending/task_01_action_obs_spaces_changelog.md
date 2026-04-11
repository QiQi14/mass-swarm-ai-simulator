# Changelog: task_01_action_obs_spaces

## Touched Files
- `macro-brain/src/env/spaces.py`

## Contract Fulfillment
- Implemented MultiDiscrete Action Space `[8, 2500]` layout via `make_action_space()`.
- Implemented 8-channel + 12-dim summary Observation Space layout via `make_observation_space()`.
- Implemented spatial utilities (`decode_spatial`, `grid_to_world`, `make_coordinate_mask`).
- Added constants for `ACTION_*` (8 vocabulary actions) and `SPATIAL_ACTIONS`.

## Deviations/Notes
- **GAP REPORTED**: Constants `GRID_WIDTH`, `GRID_HEIGHT`, and `NUM_DENSITY_CHANNELS` have been removed from `spaces.py` as per the spec, BUT other files are trying to import them, leading to `ImportError` on load. The specific files dependent on the old constants include:
  - `macro-brain/src/utils/vectorizer.py`
  - `macro-brain/src/training/curriculum.py`
  - `macro-brain/src/training/callbacks.py`
  - Also, `tests/test_spaces.py` inside `macro-brain` does not actually exist yet, so the suggested `pytest` command failed.
- Due to strict Scope Isolation rules (Rule 1), I *did not modify* those out-of-scope dependents. The QA agent or Planner must generate follow-up tasks to refactor those files so the environment successfully loads.
