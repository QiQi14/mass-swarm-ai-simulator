Task_ID: C2
Execution_Phase: 3
Model_Tier: basic
Target_Files:
  - train.sh
Dependencies: C1
Context_Bindings:
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Create `train.sh` explicitly mapping the shell script defined in the spec `implementation_plan_feature_2.md`.
  2. Implement trap for clean shutdown of processes.
  3. Ensure wait blocks correctly poll ports 5555 and 8080.
  4. Make the script executable.
Verification_Strategy:
  Test_Type: manual_steps
  Test_Stack: bash
  Acceptance_Criteria:
    - CLI arguments parsed without failure
    - ZMQ Wait loop detects port correctly
    - Ctrl+C cleanly exits spawned Rust process
  Suggested_Test_Commands:
    - ./train.sh --help
    - ./train.sh --no-visualizer --timesteps 0
