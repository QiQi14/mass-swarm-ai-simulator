# Task 08: PPO Training Loop

**Task_ID:** `task_08_ppo_training`
**Execution_Phase:** 4
**Model_Tier:** `standard`
**Target_Files:**
  - `macro-brain/src/training/train.py` (NEW)
  - `macro-brain/src/training/callbacks.py` (NEW)
**Dependencies:** Task 06 (SwarmEnv), Task 07 (ZMQ protocol)
**Context_Bindings:**
  - `implementation_plan_feature_3.md` → Task 08 section

## Strict Instructions

See `implementation_plan_feature_3.md` → **Task 08: PPO Training Loop** for full instructions.

**Summary:**
1. Create `train.py` — SB3 PPO with `MultiInputPolicy`, `Discrete(8)` action space
2. Create `callbacks.py` — TensorBoard logging, checkpoint saving, episode stats
3. CLI interface: `--timesteps`, `--max-steps`, `--checkpoint-dir`
4. Register SwarmEnv with Gymnasium

## Key Decisions
- **Q1 Resolved:** SB3 (not RLlib) for Phase 3
- **Q5 Resolved:** Discrete(8) with preset parameter templates

## Verification_Strategy
```
Test_Type: integration
Test_Stack: pytest (Python)
Acceptance_Criteria:
  - train.py runs without import errors
  - PPO initializes with MultiInputPolicy
  - Callback logs to TensorBoard
  - Checkpoint files saved to specified directory
  - Can run 100 timesteps without crash (with mock env)
Suggested_Test_Commands:
  - "cd macro-brain && python -m pytest tests/test_training.py -v"
```
