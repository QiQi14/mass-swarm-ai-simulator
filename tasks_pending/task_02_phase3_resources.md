# Task 02: Phase 3 Resource Scaffolding + EngineOverride

**Task_ID:** `task_02_phase3_resources`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `basic`
**Target_Files:**
  - `micro-core/src/components/engine_override.rs` (NEW)
  - `micro-core/src/components/mod.rs` (MODIFY)
  - `micro-core/src/config.rs` (MODIFY)
  - `micro-core/src/systems/directive_executor.rs` (NEW — resource type only)
  - `micro-core/src/systems/mod.rs` (MODIFY)
**Dependencies:** None
**Context_Bindings:**
  - `implementation_plan_feature_1.md` → Task 02 section

## Strict Instructions

See `implementation_plan_feature_1.md` → **Task 02: Phase 3 Resource Scaffolding + EngineOverride** for full instructions.

**Summary:**
1. Create `EngineOverride` component in `components/engine_override.rs`
2. Add to `config.rs`: `ActiveZoneModifiers`, `ZoneModifier`, `InterventionTracker`, `FactionSpeedBuffs`, `AggroMaskRegistry` (with `is_combat_allowed`), `ActiveSubFactions`
3. Create `systems/directive_executor.rs` with ONLY the `LatestDirective` resource type (system function added by T05)
4. Register all new modules in `mod.rs` files

**Critical:** NO system logic. Data-only structs. This task enables T11 to run in Phase 1.

## Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - EngineOverride component compiles with Vec2 and Option<u32>
  - All 6 resource types implement Default
  - AggroMaskRegistry.is_combat_allowed returns true when mask missing
  - AggroMaskRegistry.is_combat_allowed returns false when explicitly denied
  - LatestDirective defaults to None
  - cargo build succeeds with no warnings
Suggested_Test_Commands:
  - "cd micro-core && cargo test engine_override"
  - "cd micro-core && cargo test config"
  - "cd micro-core && cargo build"
```
