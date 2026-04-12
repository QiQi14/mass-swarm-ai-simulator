---
Task_ID: task_01_split_context
Execution_Phase: 1
Model_Tier: basic
---

# Task 01: Split Context

## Target_Files
- .agents/context/

## Context_Bindings
- context/project/

## Strict_Instructions
1. Read the implementation plan.
2. Split large markdown files like engine-mechanics.md and training-curriculum.md into modular topic-specific files.
3. Organize files into `engine/`, `training/`, and `project/` directories.
4. Create `index.md` files for each directory.
5. Update file references in .agents/workflows and context.md to reflect the new structure.

## Verification_Strategy
- Check that all workflows have updated `.agents/context/` references.
- Verify directories are fully indexed and the legacy flat files are removed.

## Live_System_Impact
`safe` — Only modifies internal AI context docs.
