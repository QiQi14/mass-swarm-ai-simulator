Task_ID: C1
Execution_Phase: 3
Model_Tier: basic
Target_Files:
  - macro-brain/src/training/train.py
Dependencies: A2, A3, B1
Context_Bindings:
  - implementation_plan_feature_2.md
Strict_Instructions:
  1. Update `train.py`'s main routine to parse args: `--profile`, `--timesteps`, `--runs-dir`.
  2. Load and validate the profile via `validate_profile`. Exit with code 1 if invalid.
  3. Generate the run directory via `create_run`.
  4. Print the training run banner as detailed in the spec.
  5. Plumb `tensorboard_dir`, `episode_log_path`, `checkpoint_dir` into the callback hooks instead of static paths.
Verification_Strategy:
  Test_Type: manual_steps
  Test_Stack: pytest / manual
  Acceptance_Criteria:
    - Script handles the --profile flag
    - Aborts immediately on invalid profile (e.g. modify JSON to assert failure)
    - Checkpoints and logs write correctly to `runs/run_XXX_XXX/`
  Suggested_Test_Commands:
    - cd macro-brain && python -m src.training.train --timesteps 0
