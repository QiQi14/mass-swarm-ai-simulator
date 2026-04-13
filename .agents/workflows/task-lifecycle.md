---
description: Task Lifecycle & State Management Workflow.
---

# WORKFLOW: TASK STATE MANAGEMENT

All task states are managed via `task_state.json` through the lock-safe utility `task_tool.sh`. No agent may edit this file manually.

## State Machine

```
PENDING → IN_PROGRESS → DONE → COMPLETE → auto-archive
                          ↓        ↓
                        FAILED ← FAILED
                          ↓
                       PENDING (reset)
```

| State | Meaning | Set By |
|-------|---------|--------|
| `PENDING` | Not started | System (init) |
| `IN_PROGRESS` | Executor is working | Executor |
| `DONE` | Code written, changelog created, ready for QA | Executor |
| `COMPLETE` | QA verified and certified | QA |
| `FAILED` | Defects found, needs revision | QA |

## Phase 0: Tool Verification

Before starting any new feature plan, verify these tools exist in the project root:
- `task_tool.sh` / `task_tool.py` — State management CLI
- `dispatch.sh` / `dispatch.py` — Agent session dispatch CLI

If either is missing, notify the user before proceeding.

## Phase 1: State Initialization (Planning Agent)

After generating the DAG and task node files, initialize the state file:

```bash
./task_tool.sh init --feature "Feature Name"
```

This scans `tasks_pending/` and creates `task_state.json` with:
- Global status: `PENDING`
- Each task: `status: PENDING`, `fail_reason: null`

## Phase 2: Execution Protocol (Executor Agents)

- Write the code, then create a changelog: `tasks_pending/[TASK_ID]_changelog.md`
- Signal ready for QA: `./task_tool.sh done [TASK_ID]`
- **DO NOT** call `complete` — that is the QA agent's command
- **Revision Loop:** If assigned a `FAILED` task, read the `fail_reason` in `task_state.json` to understand what needs fixing before re-attempting

## Phase 3: QA Verification (QA Agents)

QA reviews each `DONE` task against its contract:
- **PASS:** `./task_tool.sh complete [TASK_ID]`
- **FAIL:** `./task_tool.sh fail [TASK_ID] --reason "[defect list]"`
- **Knowledge Capture:** Document any lessons learned in `.agents/knowledge/`

## Phase 4: Auto-Cleanup & Archive

Agents DO NOT manually clean up the root directory.
- When QA marks the FINAL task as `COMPLETE` (with zero failures), `task_tool.sh` autonomously archives all artifacts to `.agents/history/<timestamp>/`.
- Archived files: `task_state.json`, `implementation_plan.md`, `tasks_pending/`.

## Phase 5: Feature Ledger Update

After archive, the feature must be recorded in `.agents/context/project/features.md` (the Logic Ledger).

- **Who:** The Planner agent, at the START of its next session (Step 0 in `planner.md`)
- **What:** A concise 3-5 line entry summarizing the feature, key decisions, and file locations
- **Why:** Future agents need to know what already exists to avoid conflicts and reuse patterns
- **Archive pointer:** Each entry links to the history folder for deep context when needed