# Task 10: Integration & End-to-End Smoke Test

**Task_ID:** `task_10_integration_smoke_test`
**Execution_Phase:** 5 (final, sequential)
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/main.rs` (MODIFY)
**Dependencies:** All previous tasks (01–09, 11, 12)
**Context_Bindings:**
  - `implementation_plan_feature_4.md` → Task 10 section (FULL)

## Strict Instructions

See `implementation_plan_feature_4.md` → **Task 10: Integration & Smoke Test** for full instructions.

**Summary:**
1. Wire all new resources and systems into `main.rs`
2. Run backward compatibility tests (cargo test, clippy, pytest)
3. Verify stub AI backward compatibility
4. Run 5000-step PPO training
5. Visual verification of all 7 directive types in debug visualizer
6. Execute all 8 patch regression tests (P1–P8)

## Verification_Strategy
```
Test_Type: integration + e2e
Test_Stack: cargo test (Rust) + pytest (Python) + manual visual
Acceptance_Criteria:
  - Phase A: cargo build + test + clippy pass
  - Phase B: Stub AI backward compatible
  - Phase C: PPO trains 5000 steps without crash
  - Phase D: All 7 directive types produce visible behavior
  - Phase E: All 8 patch regression tests pass
Suggested_Test_Commands:
  - "cd micro-core && cargo test"
  - "cd micro-core && cargo clippy -- -D warnings"
  - "cd macro-brain && python -m pytest tests/ -v"
```
