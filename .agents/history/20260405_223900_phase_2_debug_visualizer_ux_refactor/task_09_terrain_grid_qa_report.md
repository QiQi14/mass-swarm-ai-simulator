---
description: Structured QA certification report template — must be filled before marking a task COMPLETE
---

# QA Certification Report: task_09_terrain_grid

> Fill this template and save as `tasks_pending/[TASK_ID]_qa_report.md` before calling `./task_tool.sh complete` or `./task_tool.sh fail`.

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | 2026-04-04 | PASS | TerrainGrid resource implemented correctly with all expected methods and unit tests passing. |

---

## Latest Verification (Attempt 1)

### 1. Build Gate
- **Command:** `cargo test terrain`
- **Result:** PASS
- **Evidence:**
```
    Finished `test` profile [unoptimized + debuginfo] target(s) in 0.09s
     Running unittests src/lib.rs (target/debug/deps/micro_core-796b71b68556a3f9)

running 9 tests
test terrain::tests::test_terrain_default_costs_are_100 ... ok
test terrain::tests::test_terrain_oob_returns_wall ... ok
test terrain::tests::test_terrain_set_cell_bounds_check ... ok
test terrain::tests::test_terrain_reset_clears_all ... ok
test terrain::tests::test_terrain_oob_returns_frozen ... ok
test terrain::tests::test_terrain_wall_returns_max ... ok
test terrain::tests::test_terrain_hard_obstacles_filters_walls ... ok
test terrain::tests::test_terrain_world_to_cell_conversion ... ok
test terrain::tests::test_terrain_serialization_roundtrip ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 81 filtered out; finished in 0.00s
```

### 2. Regression Scan
- **Prior Tests Found:** None found
- **Reused/Adapted:** N/A

### 3. Test Authoring
- **Test Files Created:** Tests were integrated in `terrain.rs` following the task instructions.
- **Coverage:** Tested default costs, wall returns, out of bounds bounds (hard and soft), obstacles filter, boundary check on set_cell, resetting, and serialization string representation. 
- **Test Stack:** `cargo test`

### 4. Test Execution Gate
- **Commands Run:** `cargo test terrain`
- **Results:** 9 passed, 0 failed, 0 skipped
- **Evidence:**
```
test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 81 filtered out; finished in 0.00s
```

### 5. Acceptance Criteria
| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | new initializes arrays with 100 | ✅ | `test_terrain_default_costs_are_100` |
| 2 | get_hard_cost OOB returns u16::MAX | ✅ | `test_terrain_oob_returns_wall` |
| 3 | get_soft_cost OOB returns 0 | ✅ | `test_terrain_oob_returns_frozen` |
| 4 | set_cell bounds check write arrays | ✅ | `test_terrain_set_cell_bounds_check` |
| 5 | hard_obstacles returns u16::MAX cells | ✅ | `test_terrain_hard_obstacles_filters_walls` |
| 6 | reset sets all costs to 100 | ✅ | `test_terrain_reset_clears_all` |
| 7 | world_to_cell conversion | ✅ | `test_terrain_world_to_cell_conversion` |

### 6. Negative Path Testing
| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| Set cell OOB constraints | Ignores command without panicking | Ignored OOB | ✅ |
| Get cell OOB (hard) | Returns `u16::MAX` | Returns `u16::MAX` | ✅ |
| Get cell OOB (soft) | Returns `0` | Returns `0` | ✅ |

### 7. Certification Decision
- **Status:** COMPLETE
- **Reason:** All mandated interface functions are successfully passing the contract, all tests integrated and assert correct behavior.
