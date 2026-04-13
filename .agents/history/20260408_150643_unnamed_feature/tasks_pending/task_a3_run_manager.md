Task_ID: A3
Execution_Phase: 1
Model_Tier: advanced
Target_Files:
  - macro-brain/src/training/run_manager.py
  - macro-brain/tests/test_run_manager.py
Dependencies: None
Context_Bindings:
  - implementation_plan.md
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Implement `RunConfig` dataclass with directory generation paths.
  2. Implement `create_run` to scaffold a timestamped directory under `runs_dir`, and copy the profile snapshot.
  3. Tests should verify filesystem creation using Pytest `tmp_path` fixture.
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest
  Acceptance_Criteria:
    - Folders created correctly with timestamp syntax
    - Profile JSON copied locally
  Suggested_Test_Commands:
    - cd macro-brain && python -m pytest tests/test_run_manager.py -v
