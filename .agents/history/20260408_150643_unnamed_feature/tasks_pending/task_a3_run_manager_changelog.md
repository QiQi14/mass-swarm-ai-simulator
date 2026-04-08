# Changelog: Task A3 (Run Manager)

## Touched Files
- `macro-brain/src/training/run_manager.py` (New): Implemented `RunConfig` dataclass and `create_run` function to scaffold timestamped training run directories.
- `macro-brain/tests/test_run_manager.py` (New): Implemented Pytest unit tests verifying directory creation, profile snapshot copy, and unique run ID generation.

## Contract Fulfillment
- `RunConfig` implemented with path generation properties (`checkpoint_dir`, `tensorboard_dir`, `episode_log_path`, `profile_snapshot_path`).
- `create_run` correctly formats the timestamped parent folder, creates required sub-directories (`checkpoints`, `tb_logs`), and copies the profile to `profile_snapshot.json`.
- Complete set of unit tests using Pytest and the `tmp_path` fixture. Tests confirm filesystem manipulation and unique run ID generation correctly.

## Deviations/Notes
- Mapped `datetime.now()` via `unittest.mock.patch` in tests to reliably test timestamps for `run_id` formatting, instead of relying on `time.sleep` inside the unit test.

## Human Interventions
- None.
