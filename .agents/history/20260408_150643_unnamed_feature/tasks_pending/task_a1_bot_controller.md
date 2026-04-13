Task_ID: A1
Execution_Phase: 1
Model_Tier: advanced
Target_Files:
  - macro-brain/src/env/bot_controller.py
  - macro-brain/tests/test_bot_controller.py
Dependencies: None
Context_Bindings:
  - implementation_plan.md
  - implementation_plan_feature_1.md
Strict_Instructions:
  1. Create `BotController` class according to the exact contract in `implementation_plan_feature_1.md`.
  2. Implement the `MIN_LOCK_STEPS = 15` hysteresis logic in the `Adaptive` strategy to prevent jitter.
  3. Implement the `_validate_bot_directive` logic IF placed here, or wait for B1 to place it in `SwarmEnv`.
  4. Write comprehensive tests in `test_bot_controller.py` validating hysteresis state changes.
Verification_Strategy:
  Test_Type: unit
  Test_Stack: pytest
  Acceptance_Criteria:
    - Adaptive mode does not switch before MIN_LOCK_STEPS
    - Generates expected inner-format dictionaries
  Suggested_Test_Commands:
    - cd macro-brain && python -m pytest tests/test_bot_controller.py -v
