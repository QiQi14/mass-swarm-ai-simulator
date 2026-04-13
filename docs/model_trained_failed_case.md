# Training Failure Cases & Post-Mortems

This document tracks significant failures encountered during RL training and how they were resolved to improve the Mass-Swarm pipeline.

### Case 1: Entropy Collapse ("Frankenstein Mode")
- **Stage**: Early Stage 1 (Target Selection)
- **Symptom**: The model's policy entropy collapsed to near 0, permanently outputting the `AttackFurthest` action regardless of the state. Win rate peaked at 73% then crashed to stabilize around 11%.
- **Root Cause**: The old `Discrete(3)` action space (`Hold`, `AttackNearest`, `AttackFurthest`) created positional biases. When evaluating scenarios, `AttackFurthest` accidentally succeeded roughly 50% of the time due to spawn heuristics, causing a positive feedback loop that destroyed gradient exploration.
- **Resolution**: Fully rewrote the action space to `MultiDiscrete([8, 2500])` atomic primitives, requiring the model to explicitly output a target index via `AttackCoord` instead of relying on a hardcoded semantic.

### Case 2: Visual Density Prior
- **Stage**: Stage 1 Training
- **Symptom**: The model consistently learned to attack the 50-unit "Trap" faction instead of the 20-unit "Target" faction, despite the Target being the mathematically correct and optimal choice.
- **Root Cause**: The CNN `TacticalExtractor` learned a naive correlation based on the `ch1` (raw unit density) map—picking the largest visual blob on screen—rather than correctly referencing `ch7` (Threat ECP Density) to assess combat risks.
- **Resolution**: Equalized both bot factions to precisely 50 units and a 50.0 spread radius, while scaling the Target HP proportionately down to 24.0. This eliminated the visual bias on `ch1` entirely, forcing the model to utilize combat metrics to succeed.

### Case 3: ZMQ Socket Deadlocks
- **Stage**: Sub-engine Rollout Collection
- **Symptom**: The Python process would silently freeze indefinitely during training loops, causing CPU utilization to flatline without throwing an exception.
- **Root Cause**: Fast RL tick intervals caused asynchronous de-syncs between the Python `SwarmEnv` wrapper and the Rust Micro-Core. Engine state interventions caused the Python client to miss frames, inducing deadlocks inside the ZeroMQ `REP` cycle.
- **Resolution**: Hardened the bridge to a strict alternating messaging topology with explicitly defined socket `RCVTIMEO` and `SNDTIMEO` thresholds, combined with a "tick swallowing" protocol. The RL environment now recovers or truncates broken episodes cleanly rather than blocking execution.
