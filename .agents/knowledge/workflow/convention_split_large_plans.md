# Lesson: Split Large Implementation Plans to Avoid Token Truncation

**Category:** workflow
**Discovered:** Debug Visualizer UX Refactor (2026-04-04)
**Severity:** high

## Context
During the Debug Visualizer UX Refactor planning, the implementation plan grew to ~780 lines across 4 critiques and 3 features. This exceeded comfortable token limits for executor agents loading the plan via `Context_Bindings`.

## Problem
A monolithic `implementation_plan.md` file that grows through multiple review iterations becomes too large for mid-tier executor agents to consume effectively. Key details get truncated or the agent runs out of context window before reaching the instructions relevant to its task.

## Correct Approach
Split the plan when it exceeds ~400 lines:

1. **Index file** (`implementation_plan.md`): High-level architecture, DAG phases, cross-cutting contracts, file summary, verification plan. ~300 lines max.
2. **Detail files** (`implementation_plan_feature_[N].md`): One per feature/component. Contains full code contracts, per-file change instructions, anti-patterns. ~300 lines each.

Task briefs reference ONLY the detail file relevant to their scope, reducing context load by 60-80%.

## Example
- ❌ One 780-line `implementation_plan.md` with 3 features + inter-layer architecture + state management
- ✅ Split into:
  - `implementation_plan.md` (overview, DAG, contracts, ~300 lines)
  - `implementation_plan_feature_1.md` (Mass Spawn details)
  - `implementation_plan_feature_2.md` (Fog of War details)
  - `implementation_plan_feature_3.md` (Terrain Editor details)
