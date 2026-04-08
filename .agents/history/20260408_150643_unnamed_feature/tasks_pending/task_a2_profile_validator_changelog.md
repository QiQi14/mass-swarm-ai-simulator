# Task A2 Profile Validator Changelog

## Touched Files
- `macro-brain/src/config/validator.py` (Created)
- `macro-brain/tests/test_validator.py` (Created)

## Contract Fulfillment
- Created the `ValidationResult` dataclass with `valid`, `errors`, and `warnings`.
- Implemented `validate_profile(profile: GameProfile) -> ValidationResult` inside `validator.py`, strictly validating V1 through V9.
- Created the CLI entry point formatting the output exactly to the expected CLI spec from the task brief.
- Implemented and successfully passed all the required unit tests for all 9 validation scenarios in `test_validator.py`.

## Deviations/Notes
- For checking the invalid world dimensions in V9, the calculation was executed per the rule using `cell_size` and `grid_width`, checking it strictly within the `10%` tolerance.
- For Action Indices array being contiguous (V5), the validation was implemented using range evaluation (`sorted(a.index) == list(range(len(profile.actions)))`).
- The `validator.py` CLI exits with code `1` when the profile is invalid and exits successfully (code `0`) when valid, to properly fail automated tests or pipelines relying on validity.
- Added a `_build_valid_profile()` mock builder to cleanly test edge-cases within `test_validator.py` while ensuring object immutability (`frozen=True`) didn't slow down the unit tests.

## Human Interventions
- None.
