---
description: Structured QA certification report template — must be filled before marking a task COMPLETE
---

# QA Certification Report: [TASK_ID]

> Fill this template and save as `tasks_pending/[TASK_ID]_qa_report.md` before calling `./task_tool.sh complete` or `./task_tool.sh fail`.

## Verification Loop

| Attempt | Date | Result | Summary |
|---------|------|--------|---------|
| 1 | YYYY-MM-DD | PASS / FAIL | [brief reason or confirmation] |

---

## Latest Verification (Attempt N)

### 1. Build Gate
- **Command:** `[exact command run]`
- **Result:** PASS / FAIL
- **Evidence:**
```
[paste terminal output]
```

### 2. Regression Scan
- **Prior Tests Found:** [list any relevant tests from `.agents/history/*/tests/INDEX.md`, or "None found"]
- **Reused/Adapted:** [list tests reused, or "N/A"]

### 3. Test Authoring
- **Test Files Created:** [list test files written by QA or dedicated test executor]
- **Coverage:** [which acceptance criteria each test covers]
- **Test Stack:** [reference to `stacks/` used]

### 4. Test Execution Gate
- **Commands Run:** [list each test command]
- **Results:** [X passed, Y failed, Z skipped]
- **Evidence:**
```
[paste relevant test output]
```

### 5. Acceptance Criteria
| # | Criterion | Verified? | Evidence |
|---|-----------|-----------|----------|
| 1 | [from Verification_Strategy] | ✅ / ❌ | [test output line, screenshot, or manual step result] |
| 2 | ... | ✅ / ❌ | ... |

### 6. Negative Path Testing
| Scenario | Expected Behavior | Actual Behavior | Pass? |
|----------|-------------------|-----------------|-------|
| Empty input | Returns [] | [actual] | ✅ / ❌ |
| Null parameter | Throws TypeError | [actual] | ✅ / ❌ |
| [boundary case] | [expected] | [actual] | ✅ / ❌ |

### 7. Certification Decision
- **Status:** COMPLETE / FAIL
- **Reason:** [if FAIL, point-by-point defect list with file:line references]

---

## Previous Attempts

<!-- Copy this block for each failed attempt to maintain loop history -->

### Attempt N — FAIL
- **Date:** YYYY-MM-DD
- **Defects Found:**
  1. [defect description with file:line reference]
  2. [defect description]
- **Executor Fix Notes:** [what was changed in the fix attempt, from the updated changelog]
