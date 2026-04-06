# QA Certification Report: task_09_reward_shaping

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | 2026-04-06 | PASS | All files created per contract. P5 Pacifist Flank Exploit fully patched with distance cutoff and attenuation. All 5 reward components correctly weighted and composed. |

---

## Latest Verification (Attempt 1)

### 1. Build Gate
- **Command:** `cd macro-brain && python -c "from src.env.rewards import flanking_bonus, compute_shaped_reward; print('OK')"`
- **Result:** PASS
- **Evidence:**
```
OK — all imports resolve, no syntax errors
```

### 2. Regression Scan
- **Prior Tests Found:** None found in `.agents/history/*/tests/INDEX.md`
- **Reused/Adapted:** N/A

### 3. Test Authoring
- **Test Files Created:**
  - `macro-brain/tests/test_rewards.py` — 5 tests covering all acceptance criteria
- **Coverage:**
  - AC1: P5 distant sub-faction returns 0.0 ← `test_patch5_pacifist_flank_exploit_blocked`
  - AC2: P5 genuine close-range flank returns > 0.0 ← `test_patch5_genuine_flank_rewarded`
  - AC3: P5 distance attenuation monotonically decreasing ← `test_patch5_distance_attenuation`
  - AC4: P5 no sub-faction density → 0.0 ← `test_patch5_no_sub_faction_zero_bonus`
  - AC5: shaped reward combines all 5 components ← `test_shaped_reward_composition`
- **Test Stack:** `pytest` (Python)

### 4. Test Execution Gate
- **Commands Run:**
  - `cd macro-brain && python -m pytest tests/test_rewards.py -v`
- **Results:** 5 passed, 0 failed, 0 skipped
- **Evidence:**
```
tests/test_rewards.py::test_patch5_pacifist_flank_exploit_blocked PASSED
tests/test_rewards.py::test_patch5_genuine_flank_rewarded PASSED
tests/test_rewards.py::test_patch5_distance_attenuation PASSED
tests/test_rewards.py::test_patch5_no_sub_faction_zero_bonus PASSED
tests/test_rewards.py::test_shaped_reward_composition PASSED
==================== 5 passed in 0.10s ====================
```

### 5. Acceptance Criteria
| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | P5: Distant sub-faction returns 0.0 flanking bonus | ✅ | `test_patch5_pacifist_flank_exploit_blocked` — sub at (49,49), enemy at (25,30), dist≈30.6 > max_engage_radius=15, returns 0.0 |
| 2 | P5: Genuine close-range flank returns > 0.0 | ✅ | `test_patch5_genuine_flank_rewarded` — sub at (30,25), enemy at (25,25), dist=5 < 15, returns > 0.0 |
| 3 | P5: Distance attenuation is monotonically decreasing | ✅ | `test_patch5_distance_attenuation` — bonus1 > bonus2 > bonus3 > 0.0 at increasing distances |
| 4 | P5: No sub-faction density → 0.0 bonus | ✅ | `test_patch5_no_sub_faction_zero_bonus` — zero density sub returns 0.0 |
| 5 | Shaped reward combines all 5 components correctly | ✅ | `test_shaped_reward_composition` — positive reward with survival, kill, territory, health, flanking components |

### 6. Negative Path Testing
| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| Zero density for own/sub/enemy | Returns 0.0 (centroid returns None) | Correct | ✅ |
| All entities same position | cos_sim check prevents division issues | Correct — near-zero vector length handled | ✅ |
| prev_snapshot is None | Survival/kill/health deltas default to 0.0 | Correct — conditionally computed | ✅ |
| No active sub-factions | Flanking bonus skipped entirely | Correct — `if sub_factions:` guard at line 153 | ✅ |

### 7. Certification Decision
- **Status:** COMPLETE
- **Code Quality Notes:**
  - `flanking_bonus()` uses `min()` builtin (line 71) instead of `np.clip()` — this is fine since it's a scalar operation, not a NumPy array operation.
  - The `compute_shaped_reward()` function uses string keys (`"0"`, `"1"`) for faction lookups from JSON dicts — correctly matches the JSON serialization format from Rust.
  - `_compute_reward` in `swarm_env.py` correctly passes `prev_snapshot` captured before `self._last_snapshot` is overwritten (line 163-164).

---

## Previous Attempts

None.
