---
description: The Execution Lifecycle
---

# WORKFLOW: EXECUTION LIFECYCLE

When assigned a task from `tasks_pending/`, follow this 4-step execution loop:

## Step 1: Assimilation (Context Sync)
- Read your assigned `tasks_pending/task_[ID].md`.
- Read the root `implementation_plan.md` ONLY to understand where your task fits in the overall architecture. Do not attempt to fulfill other agents' tasks.
- Identify your exact target files and the strict contracts you must fulfill.

## Step 2: Implementation (Drafting)
Write the code required to fulfill the task.
- Adhere to the Workspace Rules regarding the specific Tech Stack (Kotlin/TS/etc.) which will be provided in your context.
- Ensure all business logic, UI state, and edge cases mentioned in the task brief are fully covered.
- Do not use placeholders like `// TODO`. Output fully functional, production-ready code.

## Step 3: Self-Review (Contract Verification)
Before finalizing, perform an internal check:
1. Did I strictly follow the function signatures and models defined in the task brief?
2. Did I accidentally leak logic or modify files outside my `Target_Files` scope?
3. (If applicable) Does my code compile/transpile logically based on the language constraints?

## Step 4: Status Reporting (Handover)
Before you mark the task as done, you must generate a handoff artifact for the QA Agent. 
1. **Create the Changelog:** Create a new file named `tasks_pending/[TASK_ID]_changelog.md`.
2. **Draft the Summary:** In this file, you MUST include:
   - **Touched Files:** A strict bulleted list of every file you created or modified.
   - **Contract Fulfillment:** A brief confirmation of the exact interfaces/DTOs you implemented.
   - **Deviations/Notes:** Any specific edge cases you handled that the QA Agent should specifically test.
   - **Human Interventions:** If a human provided code, redirected your approach, or overrode a spec decision during execution, document each intervention:
     - What the human proposed
     - What you adopted vs. what you corrected (verify details!)
     - Any deviations from the original task brief
     - If no human interventions occurred, write "None."
3. **Signal Ready for QA:** Only AFTER the changelog file is successfully written, run:
   ```bash
   ./task_tool.sh done [TASK_ID]
   ```
   > **Note:** This marks the task as DONE (awaiting QA), NOT complete. The QA agent will call `complete` after verification.
4. Halt execution.