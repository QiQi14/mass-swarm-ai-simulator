# Rule: Always Archive Tasks Through task_tool.sh

**Category:** Core Convention, State Management

## Context
During Phase 3 cleanup, an agent manually moved task files from `tasks_pending/` to `.agents/history/` using `mv`, bypassing `task_tool.sh`. This caused:
1. **6 tasks stuck at `DONE` state** were archived without being promoted to `COMPLETE` — losing the QA verification audit trail.
2. **`task_state.json` was deleted** instead of being properly archived by the tool.
3. The `.dispatch/` prompts were moved without the tool's archival metadata.

## Strict Directive
**NEVER manually move, delete, or rename files managed by `task_tool.sh`.** Always use the proper lifecycle:

```bash
# 1. Executor finishes → mark DONE
./task_tool.sh done <task_id>

# 2. QA verifies → mark COMPLETE
./task_tool.sh complete <task_id>

# 3. When ALL tasks are COMPLETE, the tool auto-archives.
#    If you need to force-archive (some still DONE/FAILED):
./task_tool.sh archive --force
```

The **only** exception is if `task_tool.sh` itself is broken or the workflow has a structural flaw. In that case, document the manual intervention explicitly.

### What `task_tool.sh archive` handles automatically:
- Moves `task_state.json` → `.agents/history/<timestamp>/`
- Moves all `implementation_plan*.md` → archive
- Moves `tasks_pending/` directory → archive
- Moves `.dispatch/` directory → archive
- Creates timestamped archive folder with feature name

## Example
- **❌ Anti-pattern:** `mv tasks_pending/* .agents/history/cleanup/tasks/` — bypasses state tracking, loses audit trail
- **✅ Best Practice:** `./task_tool.sh complete <task_id>` for each verified task → tool auto-archives when all complete
- **✅ Force archive:** `./task_tool.sh archive --force` if some tasks are not COMPLETE but you need to move on
