# QA Certification Report: task_10_game_profile

> Fill this template and save as `tasks_pending/[TASK_ID]_qa_report.md` before calling `./task_tool.sh complete` or `./task_tool.sh fail`.

## Verification Loop

| Attempt | Date       | Result | Summary                                                              |
| ------- | ---------- | ------ | -------------------------------------------------------------------- |
| 1       | 2026-04-10 | PASS   | Successfully verified tactical curriculum JSON and removed old ones. |

---

## Latest Verification (Attempt 1)

### 1. Build Gate

- **Command:** N/A (JSON validation via Python parser during tests)
- **Result:** PASS
- **Evidence:**
  ```text
  Valid JSON, successfully parsed by src.config.game_profile.load_profile.
  ```

### 2. Regression Scan

- **Prior Tests Found:** None applicable specifically to this new asset, but integrated into existing profile validation.
- **Reused/Adapted:** N/A

### 3. Test Authoring

- **Test Files Created:** `macro-brain/tests/test_game_profile_task10.py`
- **Coverage:** Tested for tactical_curriculum.json existence, parsing correctness, exact structure (8 actions, 8 stages, 3 factions), correct variables (lure action, approach scale, lure bonus, win rate), and the successful deletion of old profiles.
- **Test Stack:** `pytest (macro-brain)`

### 4. Test Execution Gate

- **Commands Run:** `cd macro-brain && .venv/bin/python -m pytest tests/test_game_profile_task10.py -v`
- **Results:** 2 passed, 0 failed, 0 skipped
- **Evidence:**
  ```text
  ============================= test session starts ==============================
  platform darwin -- Python 3.14.3, pytest-9.0.3, pluggy-1.6.0 -- /Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain/.venv/bin/python
  cachedir: .pytest_cache
  rootdir: /Users/manifera/Documents/GitHub/mass-swarm-ai-simulator/macro-brain
  collecting ... collected 2 items

  tests/test_game_profile_task10.py::test_tactical_curriculum_profile_loads_and_has_correct_structure PASSED [ 50%]
  tests/test_game_profile_task10.py::test_old_profiles_deleted PASSED      [100%]

  ============================== 2 passed in 0.02s ===============================
  ```

### 5. Acceptance Criteria

| #   | Criterion                                              | Verified? | Evidence                                                                |
| --- | ------------------------------------------------------ | --------- | ----------------------------------------------------------------------- |
| 1   | Profile loads without errors                           | ✅         | `load_profile` succeeds with `Profile is not None`                      |
| 2   | Profile has 8 actions                                  | ✅         | `profile.num_actions == 8` passed                                       |
| 3   | Profile has 8 curriculum stages                        | ✅         | `len(profile.training.curriculum) == 8` passed                          |
| 4   | Profile has 3 factions (Brain/Trap/Target)             | ✅         | Verified factions logic via tests                                       |
| 5   | actions[7].name == 'Lure'                              | ✅         | Verified via `profile.actions[7].name == 'Lure'`                        |
| 6   | rewards.approach_scale == 0.02                         | ✅         | Verified via `profile.training.rewards.approach_scale == 0.02`          |
| 7   | rewards.lure_success_bonus == 3.0                      | ✅         | Verified via `profile.training.rewards.lure_success_bonus == 3.0`       |
| 8   | curriculum[6].graduation.win_rate == 0.75 (Stage 7)    | ✅         | Verified via `profile.training.curriculum[6].graduation.win_rate == 0.75` |
| 9   | Old profiles deleted or deprecated                     | ✅         | Verified the non-existence of `stage1_tactical.json` and `default_...`  |

### 6. Negative Path Testing

| Scenario                                                                   | Expected Behavior | Actual Behavior      | Pass? |
| -------------------------------------------------------------------------- | ----------------- | -------------------- | ----- |
| Loading missing profiles (`stage1_tactical`, etc.)                         | FileNotFound      | Profile not on disk. | ✅     |

### 7. Certification Decision

- **Status:** COMPLETE
- **Reason:** All changes match the contract explicitly. Data types and constraints line up perfectly with test structures. Old files are cleanly removed without residue.
