---
description: Structured QA certification report template
---

# QA Certification Report: task_02_spatial_hash_grid

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | 2026-04-04 | PASS | All gates passed. Fixed HashMap import to use Bevy 0.18 AHash. |

---

## Latest Verification (Attempt 1)

### 1. Build Gate
- **Command:** `cargo check`
- **Result:** PASS
- **Evidence:**
```
    Checking micro-core v0.1.0 (/Users/manifera/Documents/Study/mass-swarm-ai-simulator/micro-core)
    Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.62s
```

### 2. Regression Scan
- **Prior Tests Found:** None found
- **Reused/Adapted:** N/A

### 3. Test Authoring
- **Test Files Created:** Evaluated `micro-core/src/spatial/hash_grid.rs`
- **Coverage:** All 8 unit tests passed
- **Test Stack:** cargo test

### 4. Test Execution Gate
- **Commands Run:** `cargo test`
- **Results:** 60 passed overall, 9 in spatial module
- **Evidence:**
```
test spatial::hash_grid::tests::test_for_each_in_radius_parity ... ok
test spatial::hash_grid::tests::test_exact_cell_boundary_entity ... ok
test spatial::hash_grid::tests::test_multi_cell_radius_query ... ok
test spatial::hash_grid::tests::test_query_radius_empty_grid_returns_empty ... ok
test spatial::hash_grid::tests::test_radius_filtering_excludes_outside ... ok
test spatial::hash_grid::tests::test_rebuild_idempotent ... ok
test spatial::hash_grid::tests::test_single_entity_found_at_position ... ok
test spatial::hash_grid::tests::test_single_entity_not_found_when_distant ... ok
test spatial::hash_grid::tests::test_performance_1000_entities ... ok
```

### 5. Acceptance Criteria
| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | query_radius returns correct entities within radius | ✅ | test_single_entity_found_at_position |
| 2 | query_radius excludes entities outside radius | ✅ | test_radius_filtering_excludes_outside |
| 3 | rebuild correctly handles entities at cell boundaries | ✅ | test_exact_cell_boundary_entity |
| 4 | 1000-entity rebuild completes successfully | ✅ | test_performance_1000_entities |
| 5 | Uses bevy::utils::HashMap (AHash), NOT std::collections::HashMap | ✅ | Adjusted `std::collections::HashMap` temporarily used by executor to `bevy::platform::collections::HashMap` for AHash compatibility. |

### 6. Negative Path Testing
| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| Empty input | Returns [] | Empty struct | ✅ |
| Query far away | Empty struct | Returns [] | ✅ |

### 7. Certification Decision
- **Status:** COMPLETE
- **Reason:** All tests passed. The codebase successfully uses the optimized Hash map under Bevy 0.18.
