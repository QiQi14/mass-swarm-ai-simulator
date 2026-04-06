# Task 04: Python Project Scaffold

**Task_ID:** `task_04_python_scaffold`
**Execution_Phase:** 1 (parallel)
**Model_Tier:** `basic`
**Target_Files:**
  - `macro-brain/requirements.txt` (MODIFY)
  - `macro-brain/src/env/__init__.py` (NEW)
  - `macro-brain/src/env/spaces.py` (NEW)
  - `macro-brain/src/utils/__init__.py` (NEW)
  - `macro-brain/src/utils/vectorizer.py` (NEW)
  - `macro-brain/src/training/__init__.py` (NEW)
  - `macro-brain/tests/__init__.py` (NEW)
  - `macro-brain/tests/test_vectorizer.py` (NEW)
**Dependencies:** None
**Context_Bindings:**
  - `implementation_plan_feature_3.md` → Task 04 section

## Strict Instructions

See `implementation_plan_feature_3.md` → **Task 04: Python Project Scaffold** for full instructions.

**Summary:**
1. Update `requirements.txt` with pyzmq, gymnasium, numpy, stable-baselines3, torch, tensorboard, pytest
2. Create package `__init__.py` files
3. Create `spaces.py` with observation space (4-channel density + terrain + summary) and action space (Discrete(8))
4. Create `vectorizer.py` that converts raw JSON snapshot → numpy observation dict (channel packing is Python's responsibility)
5. Write `test_vectorizer.py` unit tests

## Verification_Strategy
```
Test_Type: unit
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - Package imports work
  - Observation space shape matches (50×50 per channel)
  - Action space is Discrete(8)
  - Vectorizer produces correct numpy arrays from mock snapshot
  - Sub-faction overflow aggregates into ch3
Suggested_Test_Commands:
  - "cd macro-brain && python -m pytest tests/test_vectorizer.py -v"
```
