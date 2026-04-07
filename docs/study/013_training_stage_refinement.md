# Study 013: Training Stage Refinement & Architectural Decoupling

## Background

During the execution of Phase 3, we noticed that while the foundational pipeline for `MaskablePPO` RL training was working, the training convergence rates were sub-optimal. The simulation would occasionally exhibit "Learned Helplessness" where the agent spammed `Hold` or `Retreat` infinitely. Furthermore, running training while visually debugging occasionally created resource contention between the `ResetEnvironment` commands and the default Bevy ECS wave spawners.

## Analysis & Decisions

To resolve these issues, we pushed a major refinement to the RL training logic, spawning mechanisms, and the simulation runtime itself.

### 1. Decoupled Training Loop (`--training` Flag)

Previously, `dev.sh` started the Micro-Core in a mode that always ran the default `wave_spawn_system`. When the Python `Macro-Brain` connected and triggered `SwarmEnv.reset()`, the Python side also dispatched `ResetEnvironment` ZMQ commands containing procedural spawns. This meant entities were double-spawning, ruining the balance of training.

**Solution:** We introduced a `--training` argument to the Rust core.
- If run normally (`./dev.sh`), the Rust core handles spawning, waves, and all visual "demo" effects.
- If run via `cargo run --release -- --training`, aesthetic systems and heuristic spawners are completely bypassed. It relies *solely* on Python's ZMQ `ResetEnvironment` to populate the map.

### 2. 5-Stage Curriculum Expansion

Our original 2-stage curriculum proved to be too steep a learning cliff. Moving from a completely flat map to a complex procedural map with 8 actions simultaneously overwhelmed the agent.

**Solution:** We expanded to a 5-Stage Curriculum.
*   **Stage 1:** Learn to fight (2 actions: Hold, Navigate). Flat map. `Retreat` is explicitly *masked/locked* in Python so the agent is forced to engage and learn that combat yields rewards. Max steps increased from 200 to 500.
*   **Stage 2:** Learn positioning. Adds `Frenzy` and `Retreat` actions (4 actions total), with dynamic procedural spawning introduced via `get_stage2_spawns()`. 
*   **Stage 3–5:** Progressively introduce procedural terrain walls, chokepoints, and the ability to dictate zone modifiers and spawn sub-factions.

### 3. Action Masking "Retreat" in Stage 1

By locking `Retreat` in `action_masks()`, we forced the PPO agent to encounter the enemy and secure `kill` rewards early in training. Without this, random exploration frequently taught the agent that the safest way to maximize survival rewards was to run to the corner of the map and stay there until the 500 steps expired.

## Summary

The result is a strictly enforced architectural decoupling: `dev.sh --watch` runs only the front-end visualizer, the Rust core runs headlessly as a slave environment using `--training`, and Python is the absolute master over spawning and episodes. The 5-stage curriculum provides a mathematically smoother gradient for the RL agent to discover advanced mechanics without falling into local minima.
