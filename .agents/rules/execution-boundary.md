---
trigger: glob
globs: **/tasks_pending/*.md
---

# RULE: EXECUTION BOUNDARY ENFORCEMENT

## 1. The "Contract is Law" Principle
- The `task_[ID].md` file is your absolute source of truth.
- You MUST strictly implement the exact data models, function signatures, and interface contracts defined in the task brief. 
- You are FORBIDDEN from altering these contracts (e.g., renaming a variable, changing a return type), because parallel agents are building interacting features based on this exact specification.
- If the contract is flawed, STOP and request an architectural review.

## 2. Strict Scope Isolation
- Look at the `Target_Files` list in your task brief. You are ONLY authorized to create, read, or modify files within that explicit scope.
- **NEVER** modify shared registry files (e.g., global routers, root dependency injection containers) unless your task brief explicitly instructs you to do so (usually reserved for the Final Integration Phase).

## 3. State Mutation Ban
- You do not manage the project plan. You execute it.
- You are STRICTLY FORBIDDEN from manually editing `task_state.json`, `implementation_plan.md`, or moving any files.
- All state updates must be done via `./task_tool.sh` — never edit JSON manually.

## 4. The Explicit Handoff Mandate
- You MUST explicitly document every single file you created, modified, or deleted.
- You cannot assume the QA Agent or the Architect knows what you did. You must leave a precise "paper trail" via the changelog.