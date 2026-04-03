---
trigger: model_decision
description: When user request verify the /tasks_pending/*.md
---

# RULE: QA AUDIT PROTOCOL

## 1. Zero-Trust Verification
- You MUST NOT begin verification until you have located and read the `[TASK_ID]_changelog.md` created by the Executor.
- If the changelog is missing, REJECT the task immediately for "Missing Handoff Documentation".
- You do not trust verbal confirmation. Every file listed in the changelog must be physically verified on the file system.

## 2. Contract Compliance
- Your primary benchmark is the original `task_[ID].md`.
- **Critical Failure:** Any deviation from the defined interface signatures, DTO structures, or file paths specified in the Task Brief.
- **Scope Violation:** If the Executor modified files NOT listed in the `Target_Files` of the Task Brief, report a boundary breach.

## 3. Mandatory Negative Testing
- Do not just verify that the feature "works". You must verify that it "fails correctly".
- Check for error handling, null safety, and edge cases specifically mentioned in the Task Brief.
- If the Executor skipped an edge case, the task is considered INCOMPLETE.

## 4. Mandatory Certification Evidence

You MUST NOT mark a task COMPLETE without producing concrete evidence for EACH of these gates:

| Gate | Required Evidence | Acceptable Formats |
|------|------------------|--------------------|
| Build | Zero compiler errors | Terminal output paste |
| Regression Scan | Check for prior archived tests | List from `.agents/history/*/tests/INDEX.md` or "None found" |
| Test Authoring | Tests written covering acceptance criteria | Test file list with coverage mapping |
| Test Execution | All tests pass + output | Test runner output paste |
| Acceptance Criteria | Each criterion verified | Test output line, screenshot, or manual step result |
| Negative Path | Edge cases handled | Test case showing graceful failure |

If ANY gate lacks evidence, the task status MUST remain DONE — you cannot promote to COMPLETE.

All evidence must be recorded in the QA Certification Report (`tasks_pending/[TASK_ID]_qa_report.md`) using the template from `.agents/workflows/qa-certification-template.md`.

## 5. Anti-Rubber-Stamping Rule

The following is an **AUTOMATIC FAIL** for QA certification:
- Using ONLY `tsc --noEmit`, `eslint`, or equivalent static analysis as your "Dynamic Audit"
- Certifying a task as COMPLETE without running at least ONE runtime test (unit test, integration test, browser/device verification, or documented manual verification)
- Certifying when the task's `Verification_Strategy` requires tests but no test files exist
- Proceeding with testing when no matching tech stack is found in `stacks/` (MUST stop and ask the user)

**Static analysis proves the code COMPILES. It does NOT prove the code WORKS.**

## 6. Tech-Stack-Specific Verification

- The `Verification_Strategy.Test_Stack` in the task brief references a specific testing framework from `stacks/`.
- You MUST use the testing framework specified by the `Test_Stack`. Do not substitute with a different framework.
- If no `Test_Stack` is specified or no matching stack exists in `stacks/`, you MUST **stop and ask the user** which testing framework/approach to use. Never guess.