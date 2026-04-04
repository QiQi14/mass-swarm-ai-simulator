# Rule: Dispatch Template vs Workflow File Distinction

**Category:** workflow
**Discovered:** QA review of task_01_ws_dependencies_and_contracts (MP2)

## Context
The multi-agent framework has two layers of executor configuration:
1. `.agents/agents/executor.md` — The **dispatch template**. Read by `dispatch.py`, rendered with task data, and written to `.dispatch/` as the complete session prompt.
2. `.agents/workflows/executor.md` — **Documentation only**. NOT used as a slash-command trigger.

## Strict Directive
1. **NEVER use `/executor` as a slash-command trigger** for executor sessions.
2. **The dispatched prompt is the ONLY input** for executor sessions. Generate via `./dispatch.sh session executor <task_id>`.
3. When modifying the executor's prompt, edit `.agents/agents/executor.md` — this is the functional template.

## Example
- ❌ Anti-pattern: Opening a new session, triggering `/executor`, then also pasting the dispatched prompt.
- ✅ Best Practice: Open a new session and provide ONLY the dispatched prompt from `.dispatch/executor__task_XX.prompt.md`.
