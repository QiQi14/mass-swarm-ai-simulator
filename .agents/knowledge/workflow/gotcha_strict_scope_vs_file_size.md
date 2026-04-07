# Lesson: Executor Strict Scope vs. Acceptance Criteria Conflict

**Category:** workflow
**Discovered:** task_p1 / task_r2 / task_r3 / task_j1
**Severity:** high

## Context
When performing "File Splitting" refactoring tasks, the Planner specifies the exact new files to be created in the `Target_Files` list. Planners might not perfectly guess how many files are needed to get below the strict `Acceptance_Criteria` line limits (e.g., <200 lines).

## Problem
Executors are bound by the "Strict Scope Isolation" rule, which explicitly forbids creating files outside the `Target_Files` list. If the new files are still too large to meet the line constraints, the executor is trapped. Usually, they choose to blindly obey `Target_Files`, resulting in the task immediately failing the QA audit's file-size regression checks.

## Correct Approach
**For Planners/Architects:** When assigning refactor tasks with strict line limits, add a clause to the `Strict_Instructions` or `Target_Files` like: "You are authorized to create additional sub-modules within the designated directory if needed to meet the line length limit." This explicitly overrides the strict scope rule for that task.

**For Executors:** If you see you will breach the `Acceptance_Criteria` but are forbidden to create more files, you MUST stop and ask the user (Architect) for an scope expansion or architectural review, rather than blindly committing an oversized file which is guaranteed to cause a QA failure.

## Example
- ❌ **What the executor did:** Blindly compacted all data configurations into `game_profile.py` because it was the only remaining target file, knowingly failing the "under 200 lines" QA criterion.
- ✅ **What it should be:** Executor pauses and asks "I need to split `game_profile.py` further to meet the 200-line limit. Am I authorized to create `profile_parser.py`?" OR the Planner pre-authorized dynamic file creation in the task brief.
