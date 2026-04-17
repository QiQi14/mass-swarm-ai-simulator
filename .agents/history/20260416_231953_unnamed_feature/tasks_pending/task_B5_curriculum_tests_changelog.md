# Task B5: Curriculum Tests Changelog

## Touched Files
- `macro-brain/src/training/curriculum.py`
- `macro-brain/profiles/tactical_curriculum.json`
- `macro-brain/tests/test_actions.py`
- `.agents/context/training/stages.md`

## Contract Fulfillment
- Updated `curriculum.py` ACTION_NAMES to v3 (Hold, AttackCoord, ZoneModifier, SplitToCoord, MergeBack, SetPlaystyle, ActivateSkill, Retreat).
- Updated `tactical_curriculum.json` actions array with new indexes and unlock stages, and updated metadata description.
- Rewrote `test_actions.py` to use `[action_type, coord, modifier]` for 3D action space verification corresponding to the modifications provided in the `macro-brain/src/env/actions.py` script.
- Added action vocabulary and updated action logic in `stages.md` according to the strategy brief.

## Deviations/Notes
- I corrected the unit testing expectations for `SetPlaystyle` aggressive and passive modifiers to assert `SetAggroMask` instead of `SetAggroMode` per actual generated directive definitions from `actions.py`. It also checks for `allow_combat` instead of `aggressive`.
