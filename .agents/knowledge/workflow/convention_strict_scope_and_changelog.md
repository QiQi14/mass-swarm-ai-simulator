# Rule: Executor Scope Violation & Missing Changelog

**Category:** workflow
**Discovered:** task_01_ws_dependencies_and_contracts (MP2)
**Severity:** high

## Context
During the execution of `task_01_ws_dependencies_and_contracts`, the executor successfully implemented the code but violated two process rules that caused a QA FAIL and project BLOCK.

## Problem
1. **Missing Changelog**: The executor finished without creating `[TASK_ID]_changelog.md`. Fixed by adding mandatory rules inline in the dispatch template (`.agents/agents/executor.md`).
2. **Scope Violation**: The executor modified `lib.rs` even though it wasn't in `Target_Files`. The Planner must include ALL files that need modification.

## Correct Approach
- All mandatory process rules (changelog, scope) are now embedded directly in the executor dispatch template's `MANDATORY PROCESS` section — visible to ALL tiers.
- **Planners** must ensure `Target_Files` includes every file that will be modified, including registry files like `lib.rs` or `mod.rs`.
- If a file must be changed but isn't in `Target_Files`, the executor must STOP and report the gap.

## Example
- ❌ What happened: Planner omitted `lib.rs` from `Target_Files`, executor modified it anyway to make the code compile.
- ✅ What it should be: Planner includes `lib.rs` in `Target_Files` with an explicit instruction step.
