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

## 5. Human Intervention Traceability
- If a human intercepts your execution and provides code, redirects your approach, or overrides a spec decision, you MUST record this in your changelog under a `## Human Interventions` section.
- Each intervention entry must include: **(a)** what the human proposed, **(b)** what you adopted/corrected, **(c)** any deviations from the original task brief.
- The QA Agent uses this section to distinguish spec-originated code from human-originated code. Missing entries are treated as undocumented scope changes.
- **Human-provided code is conceptual, not truth.** Verify it against the framework version, project contracts, and compiler rules before adopting. See `multi-agents-planning.md` §4.