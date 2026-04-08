Task_ID: A2
Execution_Phase: 1
Model_Tier: advanced
Target_Files:
  - macro-brain/src/config/validator.py
  - macro-brain/tests/test_validator.py
Dependencies: None
Context_Bindings:
  - implementation_plan.md
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Create `ValidationResult` dataclass.
  2. Implement `validate_profile(profile: GameProfile) -> ValidationResult` evaluating exactly the 9 validation rules V1-V9 in `implementation_plan_feature_2.md`.
  3. Create CLI main block to read profile and print output formatted as requested.
  4. Write unit tests for all 9 validation scenarios.
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest
  Acceptance_Criteria:
    - Valid profile returns valid=True
    - Errors report valid=False cleanly
  Suggested_Test_Commands:
    - cd macro-brain && python -m pytest tests/test_validator.py -v
