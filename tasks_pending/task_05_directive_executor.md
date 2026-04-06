# Task 05: Directive Executor & Engine Override Systems

**Task_ID:** `task_05_directive_executor_system`
**Execution_Phase:** 2
**Model_Tier:** `advanced`
**Target_Files:**
  - `micro-core/src/systems/directive_executor.rs` (MODIFY — append system functions to T02 scaffold)
  - `micro-core/src/systems/engine_override.rs` (NEW)
  - `micro-core/src/systems/mod.rs` (MODIFY)
  - `micro-core/src/systems/movement.rs` (MODIFY)
  - `micro-core/src/rules/interaction.rs` (MODIFY)
  - `micro-core/src/rules/navigation.rs` (MODIFY)
**Dependencies:** Task 01 (MacroDirective types), Task 02 (Resource types + EngineOverride)
**Context_Bindings:**
  - `implementation_plan_feature_1.md` → Task 05 section (FULL — includes all 4 patch details)
  - `skills/rust-code-standards`
  - `skills/ecs_safety_patterns.md`

## Strict Instructions

See `implementation_plan_feature_1.md` → **Task 05: Directive Executor & Engine Override Systems** for full instructions.

**Summary:**
1. Add `directive_executor_system` to `directive_executor.rs` (appending to T02's `LatestDirective` resource)
2. Add `engine_override_system` to `engine_override.rs`
3. Add `zone_tick_system` and `speed_buff_tick_system`
4. Modify `movement.rs` with `Without<EngineOverride>` filter + speed buff
5. Modify `interaction.rs` with `AggroMaskRegistry` check
6. Modify `navigation.rs` with `NavigationTarget` enum

## CRITICAL: Four Mandatory Safety Patches
- **P1 VAPORIZATION:** Use `latest.directive.take()` — consume once
- **P2 MOSES EFFECT:** `if current_cost == u16::MAX { continue; }` in zone overlay
- **P3 GHOST STATE:** MergeFaction purges ALL registry entries
- **P4 f32 SORT:** `select_nth_unstable_by` with `partial_cmp` for SplitFaction

## Verification_Strategy
```
Test_Type: unit
Test_Stack: cargo test (Rust)
Acceptance_Criteria:
  - All 8 directive types handled correctly
  - P1: Directive consumed on first read, None on second
  - P2: u16::MAX tiles immune to zone modifier cost changes
  - P3: MergeFaction purges ALL registries
  - P4: SplitFaction uses Quickselect, correct count selection
  - 22 tests total (14 standard + 8 regression)
Suggested_Test_Commands:
  - "cd micro-core && cargo test directive_executor"
  - "cd micro-core && cargo test engine_override"
  - "cd micro-core && cargo test interaction"
  - "cd micro-core && cargo test movement"
```
