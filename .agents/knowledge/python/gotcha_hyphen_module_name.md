# Lesson: Python Cannot Import Modules with Hyphens in Directory Names

**Category:** gotcha
**Discovered:** QA audit 2026-04-06 — task_04_python_scaffold
**Severity:** medium

## Context
The `macro-brain` Python package directory contains a hyphen, which makes it impossible to use standard `import macro-brain.src.env.spaces` syntax.

## Problem
Python module names cannot contain hyphens (`-`). The `macro-brain` directory is valid as a filesystem path but invalid as a Python module name. Import statements like `from macro_brain.src.env.spaces import ...` will fail because the actual directory is `macro-brain` (with hyphen), not `macro_brain` (with underscore).

## Correct Approach
The executor correctly worked around this by:
1. Using `PYTHONPATH=.` to set the macro-brain directory as the import root
2. Using relative-style imports: `from src.env.spaces import ...` (without the top-level directory)

All Python code within `macro-brain/` must use `from src.*` imports, NOT `from macro_brain.*` or `from macro-brain.*`.

When running tests: `cd macro-brain && PYTHONPATH=. python -m pytest tests/ -v`

## Example
- ❌ `from macro_brain.src.env.spaces import make_observation_space`
- ❌ `from macro-brain.src.env.spaces import make_observation_space`
- ✅ `from src.env.spaces import make_observation_space`
