# Strategy Brief: Training Restart & Environment Clean-Up

## Problem Statement

The user requested to start training fresh at full speed and remove all stale data, acting upon the requirements outlined in the Phase Update (`TRAINING_STATUS.md` noted that a fresh start was required due to the v4.0 observation channel overhaul).

## Execution Actions

1. **Stale Data Purge**: 
   - `macro-brain/runs/`
   - `macro-brain/saved_checkpoints/`
   - `.pytest_cache/`
   - `__pycache__/`
   All previous logs and checkpoints have been permanently deleted to ensure no conflicting weights or corrupt replay buffer data interferes with the new 8-channel observation model.

2. **Environment Port Collision Fixed**:
   - Initial attempts to spawn training resulted in `micro-core`'s ZMQ Bridge panicking with `Failed Greeting exchange`. 
   - Root cause: Port `5555` was occupied by a system `qemu-system`/`adb` process holding a standard ADB interface.
   - Fix: Global port swap in both `swarm_env.py` and `io_loop.rs` from `tcp:5555` to `tcp:5556`. 
   
## Verification

- **Rust Micro-Core**: Successfully compiled and connected on `:5556`.
- **Python ML**: `MaskablePPO` successfully bootstrapped on CPU. Wait loop completed. Episode 1 has begun.
- **Speed Mode**: The `--slow-train` and `--no-visualizer` arguments were passed to `train.sh`, which suppresses the 60 TPS throttle inside Rust, unlocking max TPS. 

Training is currently running persistently in the background.
