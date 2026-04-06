# Task 01: MacroDirective Protocol

**Task_ID:** `task_01_macro_directive_protocol`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/bridges/zmq_protocol.rs` (MODIFY)
**Dependencies:** None
**Context_Bindings:**
  - `implementation_plan_feature_1.md` → Task 01 section
  - `skills/rust-code-standards`

## Strict Instructions

See `implementation_plan_feature_1.md` → **Task 01: MacroDirective Protocol** for full instructions.

**Summary:** Add the `NavigationTarget` enum, `MacroDirective` enum (8 variants with serde `tag = "directive"`), `ZoneModifierSnapshot` struct, and extended `StateSnapshot` fields to `zmq_protocol.rs`. Write 12 unit tests for all variants round-tripping through serde.

**Anti-pattern:** Do NOT remove existing `MacroAction`. Task 07 handles migration.

## Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - All 8 MacroDirective variants serde roundtrip correctly
  - NavigationTarget both variants roundtrip correctly
  - JSON uses "directive" tag key, NavigationTarget uses "type" tag key
  - Existing MacroAction tests still pass
Suggested_Test_Commands:
  - "cd micro-core && cargo test zmq_protocol"
```
