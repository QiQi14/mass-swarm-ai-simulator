```yaml
Task_ID: task_01_training_speed_throttle
Execution_Phase: 1
Model_Tier: basic
Target_Files:
  - macro-brain/profiles/default_swarm_combat.json
Dependencies: []
Context_Bindings: []
```

## Strict Instructions

1. **Modify `macro-brain/profiles/default_swarm_combat.json`**
   - Locate the `"combat": { "rules": [...] }` array.
   - For all elements in the `rules` array, change `delta_per_second` from `-25.0` to `-5.0`.
   - Locate the `"movement": { ... }` object.
   - Change `max_speed` from `60.0` to `20.0`.

2. **Start the ML Training Script**
   - Open a terminal and run the training script to begin the first stage. Since we are observing, we can run it without detaching.
   - Use the `run_command` tool to execute: `./train.sh --timesteps 500000`
   - **Crucially**, wait a few seconds and check the `command_status` to ensure it boots up properly.

## Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: manual_steps
  Test_Stack: bash
  Acceptance_Criteria:
    - "Combat rule delta_per_second is updated to -5.0 for both symmetric rules."
    - "Movement max_speed is updated to 20.0."
    - "The train.sh script runs successfully and starts generating ML training checkpoints or status logs."
  Manual_Steps:
    - "Run `cat macro-brain/profiles/default_swarm_combat.json` and verify the values."
    - "Observe the output of the terminal running `./dev.sh --watch` and `./train.sh` to confirm the speed is visibly reduced."
```
