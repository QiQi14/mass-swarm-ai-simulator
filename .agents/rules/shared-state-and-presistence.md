---
trigger: glob
description: Only use when user request new feature, refactor or complex task.
globs: **/task.md, **/implementation_plan.md
---

# RULE: SHARED STATE & FILE OWNERSHIP

## 1. Root-Level Shared State (Two-Phase Lifecycle)
- **Strategy brief:** During analysis, `strategy_brief.md` lives as an Antigravity artifact. After user approval, it is placed in the project ROOT as `strategy_brief.md` for the Planner to consume.
- **Implementation plan:** During planning, `implementation_plan.md` lives as an Antigravity artifact (`<appDataDir>/brain/<conversation-id>/implementation_plan.md`) with `RequestFeedback: true`. After user approval, it is **copied** to the project ROOT. Only the root-level copy is visible to Executor and QA agents.
- `task_state.json` is always in the project ROOT (managed by `task_tool.sh`).
- DO NOT rely on chat memory to pass instructions between agents. If it is not in a file in the root, it does not exist for the next agent.

## 2. File Ownership
- Only the **Strategist Agent** may create or modify `strategy_brief.md`.
- Only the **Planning Agent** may create or modify `implementation_plan.md`.
- Only `task_tool.sh` may modify `task_state.json`.
- The **Strategist** may update `.agents/context/engine-mechanics.md` and `.agents/context/training-curriculum.md` (research outputs).
- **Execution Agents** are strictly read-only on all shared state files.

## 3. Post-Task Archival
- No feature is considered "Complete" until all artifacts are archived to `.agents/history/`.
- This is handled automatically by `task_tool.sh` — agents do not move files manually.