Task_ID: C3
Execution_Phase: 3
Model_Tier: basic
Target_Files:
  - TRAINING_STATUS.md
Dependencies: B1
Context_Bindings:
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Complete a full rewrite of `TRAINING_STATUS.md`.
  2. Update architecture section, reflecting 50v50 entity scale.
  3. Add Phase 3.5 to completed phases.
  4. Document the exact 5-stage curriculum.
  5. Document the 4 heuristics and the zero-sum reward components.
  6. Add How-to-Train section pointing to `train.sh`.
Verification_Strategy:
  Test_Type: manual_steps
  Test_Stack: markdown
  Acceptance_Criteria:
    - No references to "300v300" remain
    - Curriculum exactly matches Phase 3.5 implementation
    - Reward equation explicitly matches python code
  Suggested_Test_Commands:
    - cat TRAINING_STATUS.md
