---
description: The Execution Lifecycle
---

# WORKFLOW: EXECUTION LIFECYCLE

When assigned a task from `tasks_pending/`, follow this 4-step execution loop:

## Step 1: Assimilation (Context Sync)
- Read your assigned `tasks_pending/task_[ID].md`.
- **CRITICAL:** Check the skills and knowledge indices (`.agents/skills/index.md` & `.agents/knowledge/README.md`). Do NOT blindly trust the Planner's `Context_Bindings`. Proactively load any relevant context missed by the Planner.
- Read the root `implementation_plan.md` ONLY to understand where your task fits in the overall architecture. Do not attempt to fulfill other agents' tasks.
- Identify your exact target files and the strict contracts you must fulfill.

## Step 1b: Live System Safety Check

> **CRITICAL:** The training pipeline (`macro-brain` → ZMQ → `micro-core`) may be running. You MUST NOT disrupt it.

### Rust Tasks (`micro-core/`)
- **DO NOT** run `cargo build` or `cargo test` — these acquire exclusive file locks on `target/` and will kill any running `cargo run` process (the training simulation).
- **USE** `cargo check` instead — it verifies compilation without linking, does not lock the binary, and is safe to run alongside a live server.
- Write all code changes, then mark task as DONE. **Full `cargo test` is QA's responsibility** and will be run in a controlled window after training is paused.
- **Exception:** If you are confident no training is running (no `dev.sh` or Rust process on port 8080), you may run `cargo test`.

### Python Tasks (`macro-brain/`)
- **DO NOT** modify function signatures or class constructors in files under `macro-brain/src/` that are actively imported by the training process (e.g., `definitions.py`, `parser.py`, `game_profile.py`, `swarm_env.py`).
- **ONLY ADD** new optional fields, new functions, or new classes. Never remove or rename existing symbols.
- All new `@dataclass` fields MUST have defaults (`= None`, `= field(default_factory=list)`) so existing profiles load without changes.
- **DO NOT** modify `tactical_curriculum.json` or any active profile — these are consumed by the live training process.

### Debug Visualizer (`debug-visualizer/`)
- Safe to modify at any time — the HTTP server serves static files and does not cache.

## Step 2: Implementation (Drafting)
Write the code required to fulfill the task.
- Adhere to the Workspace Rules regarding the specific Tech Stack (Kotlin/TS/etc.) which will be provided in your context.
- Ensure all business logic, UI state, and edge cases mentioned in the task brief are fully covered.
- Do not use placeholders like `// TODO`. Output fully functional, production-ready code.

> **⚠️ WORKSPACE HYGIENE** 
> If you need to create standalone temporary `.py`, `.rs`, or `.js` test scripts to quickly verify logic, simulate API calls, or run isolated experiments during development, **DO NOT dump them in the repository root or project source folders**. You MUST create and place all scratch files inside `.agents/scratch/`. Keep the main source tree clean.

## Step 3: Self-Review (Contract Verification)
Before finalizing, perform an internal check:
1. Did I strictly follow the function signatures and models defined in the task brief?
2. Did I accidentally leak logic or modify files outside my `Target_Files` scope?
3. (If applicable) Does my code compile/transpile logically based on the language constraints?

> **Tip:** Use `-- --nocapture` or `-- --show-output` flags when debugging test failures that need full verbose output.
>
> **⚠️ For Rust tasks:** Prefer `cargo check` over `cargo test` during self-review when training is running. See Step 1b.

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