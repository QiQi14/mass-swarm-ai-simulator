# Rule: RL Environment Safety Patterns

**Category:** Architecture, RL, Safety, Python

## Context
During Phase 3 planning, four critical vulnerabilities were identified in the Gymnasium environment and reward function that would cause reward hacking, state desynchronization, deadlocks, and MDP corruption.

## Strict Directive

### 1. PACIFIST FLANK GUARD: Proximity-Gated Rewards
When rewarding spatial strategies (flanking, encirclement):
- **❌ Anti-pattern:** Reward based only on geometric projection (angle/direction) without distance check.
  - RL agents will exploit this by positioning units at maximum distance along the projection axis.
- **✅ Best Practice:** Always combine geometric check with distance cutoff AND distance attenuation.
  - Distance cutoff: `if dist > max_engage_radius: return 0.0`
  - Attenuation: `bonus *= max(0, (max_r - dist) / max_r)`

### 2. CONTEXT-AWARE ACTIONS: Dynamic Parameterization
When mapping discrete actions to parameterized directives:
- **❌ Anti-pattern:** Hardcoded coordinates/parameters (e.g., `epicenter = [800, 500]`).
  - If the swarm is at (200, 200), the action has no effect → agent learns "this action is useless."
- **✅ Best Practice:** Calculate parameters dynamically from the current observation state.
  - Use density centroid for spatial targets, relative offsets for flanking positions.

### 3. SINGLE SOURCE OF TRUTH: Never Duplicate Cross-Process State
When tracking state that exists in another process (Rust/C++/Game Engine):
- **❌ Anti-pattern:** Local Python counters/lists tracking what should exist in Rust.
  - Entity death, merges, or failed commands desynchronize the local state.
- **✅ Best Practice:** Read ephemeral state directly from the incoming observation/snapshot.
  - `self._active_sub_factions = snapshot["active_sub_factions"]` (every step)

### 4. ZMQ REP SOCKET DISCIPLINE: Strict recv→send Alternation
When using ZMQ REP sockets for RL environments:
- **❌ Anti-pattern:** Calling `send` before `recv`, or skipping a `send` after `recv`.
- **✅ Best Practice:** Every `recv` MUST be followed by exactly one `send`. In tick swallowing loops, each iteration does `recv → send(Hold)`.
- **❌ Anti-pattern:** No timeout on `recv` → deadlock if the other process pauses/crashes.
- **✅ Best Practice:** Set `zmq.RCVTIMEO`. On timeout, close socket, recreate, return `truncated=True` to SB3.

### 5. MDP PURITY: Never Let Non-Physics Events Into The Training Buffer
When Engine overrides/interventions occur:
- **❌ Anti-pattern:** Returning `reward = 0.0` to SB3 during an intervention.
  - SB3 trains on this (state, action, 0.0 reward) tuple, falsely associating the agent's action with terrible outcomes.
- **✅ Best Practice:** Tick Swallowing — loop inside `step()`, replying `Hold` to Rust until `intervention_active == false`. SB3 never sees the intervention.
