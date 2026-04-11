---
description: The QA & Assembly Loop
---

# WORKFLOW: QA VERIFICATION

Follow this 6-step workflow to certify a task and capture lessons:

## Step 1: Handoff Analysis (Discovery)
- Locate `tasks_pending/[TASK_ID]_changelog.md`.
- Extract the list of "Touched Files" and the "Contract Fulfillment" notes.
- Verify that the list of modified files matches the authorized scope in the original `task_[ID].md`.

## Step 2: Static Code Audit (Contract vs. Reality)
- Open each modified file. 
- Compare the code side-by-side with the Contract in the planning phase.
- **Checklist:**
  - Are variable names, types, and function signatures identical to the contract?
  - Is the logic placed in the correct layer (e.g., Domain vs. Data)?
  - Are there any leftover `// TODO` or placeholders?

## Step 3: Functional Validation (Dynamic Testing)

> **CRITICAL:** Static analysis (tsc, eslint, gradle build) proves code COMPILES, not that it WORKS. Passing a build check alone is NEVER sufficient to certify a task.

### Step 3A: Build Gate (Prerequisite — Not Sufficient)
- Run the build/compile check (`cargo build`, `cargo clippy`, etc.).
- This is a **prerequisite**, not a pass condition. Passing this alone is NOT enough to certify.
- **⚠️ Training Safety:** Before running `cargo test` or `cargo build`:
  1. Check if training is running: `lsof -i :8080 2>/dev/null | grep -q LISTEN && echo "TRAINING ACTIVE — DO NOT cargo test"`
  2. If training is active, ask the user to pause training first, OR use `cargo check` (compile-only, no linking, safe to run during training).
  3. Only proceed with `cargo test` after confirming no active training session.

### Step 3B: Regression Scan (Reuse Prior Tests)
- Before writing new tests, scan `.agents/history/*/tests/INDEX.md` for previously archived tests relevant to the same feature area or files.
- If relevant prior tests exist:
  - Copy them into the working directory.
  - Run them first to establish a regression baseline.
  - Adapt or extend them for the current task's acceptance criteria.
- This reduces redundant test authoring and catches regressions in frequently changed features.

### Step 3C: Test Authoring (QA Writes Tests)
- Read the task's `Verification_Strategy` section from the task brief.
- If `Verification_Strategy` is missing, infer what to test from the task's `Strict_Instructions` and contract. Missing strategy is NOT an excuse to skip testing.
- Identify the `Test_Stack` reference. If no matching tech stack is found in `stacks/`, **STOP and ask the user** which testing framework to use. Never guess.
- If the Planner created a dedicated test task, use those test files instead of writing new ones.
- Based on `Test_Type` and `Acceptance_Criteria`, **write test files** that cover:
  - Each acceptance criterion as a test case
  - At least one negative/edge case (empty input, null, boundary)
- Place test files alongside the implementation (following project conventions from `Test_Stack`).
- If `Test_Type` is `manual_steps`, skip to Step 3E.

### Step 3D: Test Execution Gate (Mandatory)
- Run the tests written in Step 3C (and any `Suggested_Test_Commands` from the task brief).
- ALL tests must pass. Capture the full output as evidence.
- If tests fail → investigate whether it's a test bug or an implementation bug:
  - **Implementation bug** → FAIL the task with the defect list.
  - **Test bug** → fix the test and re-run.
  - **Need more detail** → Re-run with `-- --nocapture` or `-- --show-output` for full verbose output.

### Step 3E: Acceptance Criteria Walkthrough (Mandatory)
- Walk through each item in `Verification_Strategy.Acceptance_Criteria`.
- For each criterion, produce **concrete evidence** (test output line, runtime output, or documented manual verification step).
- If `Test_Type` is `manual_steps`: execute each step using **browser/device control tools** if needed (not just visual inspection) and document the result.
- For complex UI bugs: use browser automation (Playwright, Puppeteer, or agent browser tools) to verify interactive behavior — screenshots and click-through evidence required.
- If ANY acceptance criterion cannot be verified → FAIL.

### Step 3F: Negative Path Validation (Enhanced)
- You must verify that the code "fails correctly", not just that it "works".
- QA must test at least:
  - Empty/null inputs (if applicable)
  - Boundary conditions mentioned in the task brief
  - State transitions (if the task involves state management)
- These should already be covered by tests written in Step 3C, but verify explicitly.

## Step 4: Certification Report & State Update

Before changing the task state, you MUST produce a **QA Certification Report**.

1. Fill out the report template from `.agents/workflows/qa-certification-template.md`.
2. Save the completed report as `tasks_pending/[TASK_ID]_qa_report.md`.
3. Then update the task state:
   - **PASS:** If all gates are green:
     ```bash
     ./task_tool.sh complete [TASK_ID]
     ```
   - **FAIL:** If bugs or contract violations are found:
     ```bash
     ./task_tool.sh fail [TASK_ID] --reason "[Point-by-point list of defects]"
     ```
4. **Cleanup Trigger:** If this is the final task, the state tool will automatically archive the artifacts (including QA reports and test files). Do not move files manually.

## Step 5: Test File Archival

QA-authored test files are **ephemeral verification artifacts**, not permanent regression tests.

After certification:
- List all test files you created in the QA report under "Test Files Created".
- When `task_tool.sh` archives on final COMPLETE, test files will be moved to `.agents/history/<timestamp>/tests/`.
- **Do NOT manually create `tests/INDEX.md`** — run the auto-generator instead:
  ```bash
  python3 .agents/scripts/gen_tests_index.py .agents/history/<archive_folder>
  ```
  This script parses all `*_qa_report.md` files and auto-generates a structured `tests/INDEX.md` with test files, coverage, results, and task mappings.

  To regenerate ALL archive indices at once:
  ```bash
  python3 .agents/scripts/gen_tests_index.py --all
  ```

> **Why archive, not keep?** Frequently changed features would accumulate outdated test files. Archiving keeps the codebase clean while maintaining full traceability via the auto-generated index.

## Step 6: Knowledge Capture

After EVERY verification (pass or fail), check if any lessons should be persisted:

- Did the executor use a **deprecated API or function**? → Capture it
- Did the executor produce **malformed or fragile code** patterns? → Capture it
- Did you find an issue caused by **outdated tooling or commands**? → Capture it
- Did you discover a **platform-specific gotcha**? → Capture it

If yes, follow `.agents/workflows/knowledge-capture.md` to write the entry in `.agents/knowledge/`.

> **Tip:** Even on PASS, capture the lesson if the executor did something that *works but is fragile* — future executors should learn the robust approach.