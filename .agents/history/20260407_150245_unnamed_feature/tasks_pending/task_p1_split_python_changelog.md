# Task P1 Changelog: Split Python Profile + Env + Curriculum

## Touched Files
- `macro-brain/src/config/game_profile.py` (Modified)
- `macro-brain/src/config/definitions.py` (New)
- `macro-brain/src/config/__init__.py` (Modified)
- `macro-brain/src/env/swarm_env.py` (Modified)
- `macro-brain/src/env/actions.py` (New)
- `macro-brain/src/env/__init__.py` (Modified)
- `macro-brain/src/training/curriculum.py` (Modified)
- `macro-brain/src/training/callbacks.py` (Modified)
- `macro-brain/src/training/train.py` (Modified)
- `macro-brain/src/env/rewards.py` (Modified)

## Contract Fulfillment
- Extracted 19 dataclasses from `game_profile.py` into `definitions.py`.
- Moved `_action_to_directive` mapping format logic from `swarm_env.py` into `actions.py` which contains helper builder functions.
- Moved `CurriculumCallback` from `curriculum.py` to `callbacks.py`.
- All tests pass, and zero logical changes were introduced.
- Strict isolation of files to the `macro-brain` module context.

## Deviations/Notes
- The `macro-brain/src/training/train.py` and `macro-brain/src/env/rewards.py` scripts had to be updated to change their imports to the new locations of the moved dataclasses and `CurriculumCallback`.
- Extracted logic in `actions.py` is implemented as deterministic directive constructor functions rather than moving the object-dependent method, fulfilling the directive format extraction without increasing coupling.

## Human Interventions
- None.
