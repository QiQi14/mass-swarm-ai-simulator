# Changelog: Task 03

## Touched Files
- `macro-brain/src/utils/vectorizer.py` [MODIFIED]
- `macro-brain/src/utils/lkp_buffer.py` [NEW]

## Contract Fulfillment
- Wrote completely new `vectorize_snapshot` logic that handles 8 channels, 12-dim summary, center-padding and fog-enabled density evaluation.
- Added `LKPBuffer` class exactly as prescribed to keep ghost trails of enemy locations when fog makes them invisible.
- No placeholders were used.

## Deviations/Notes
- **GAP DETECTED**: The `tests/test_vectorizer.py` and `tests/test_lkp_buffer.py` files were listed in `Suggested_Test_Commands` in the Task Brief but were **NOT** included in the `Target_Files` list. As per Rule 1, I cannot modify `test_vectorizer.py` or create `test_lkp_buffer.py`.
- Running the suggested test command fails because `tests/test_vectorizer.py` is trying to import `GRID_WIDTH` from `src.env.spaces` which fails (likely out of sync with recent changes). The tests thus require an update in a separate task.
