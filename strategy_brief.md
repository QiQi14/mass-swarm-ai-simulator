# Strategy Brief: Curriculum Design for Stages 2 & 3

## Problem Statement

The tactical curriculum is advancing to Stage 2 (Pheromone Path) and Stage 3 (Repellent Field). The objective is to finalize the map configurations and reward calculations to ensure the reinforcement learning (RL) model is forced to learn `DropPheromone` and `DropRepellent` without finding any brute-force exploits or falling into local minima.

## Analysis & Diagnosis

### 1. The Zone Mechanism Duration Mismatch (CRITICAL)
- **Evidence:** `engine-mechanics.md` shows Pheromone/Repellent (`SetZoneModifier`) has a hardcoded `ticks_remaining: 120`. 
- **Math:** 1 RL step correlates to `150 physics ticks` (from frame_skip=5 × 30 ticks/skip).
- **Impact:** Any zone modifier the agent drops will disappear **before the next RL step evaluates**. The swarm mathematically cannot redirect and traverse a path in less than 1 RL step. Thus, the abilities are functionally useless right now.

### 2. Action Persistence Error
- **Issue:** If the RL model outputs `DropPheromone`, the Python envelope sends down `SetZoneModifier`. Because the system expects 1 directive per faction, sending a zone modifier drops the `UpdateNavigation` directive. The swarm will immediately idle.
- **Fix Required:** Abilities should overlay on movement.

### 3. Stage 2 (Pheromone Path) Brute-Force Check
- **Analysis:** Top path is shortest (cost=100/cell) but blocked by a 40×200HP trap fleet. Bottom path is a detour (cost=100/cell base, soft_cost=40 mud speed reduction).
- **Combat Math:** Brain (50×100HP, DPS=1250) vs Trap (40×200HP, DPS=1000). Brain head-on kill time = 6.4s, Trap kill time = 5.0s. The Brain dies.
- **Conclusion:** Stage 2 is securely designed. Because normal pathfinding (Dijkstra) always chooses the shortest physical route, the swarm will naturally route top and die. They MUST use `DropPheromone` (-50 cost modifier) on the bottom path to dynamically make it cheapest, forcing the pathfinder to bypass the trap.

### 4. Stage 3 (Repellent Field) Brute-Force Vulnerability
- **Issue in `curriculum.py`:** The `_terrain_open_with_danger_zones` sets the hard cost of the danger areas (where traps spawn) to `300`.
- **The Exploit:** The Rust engine's flow field pathfinder operates on `hard_cost`. Since the danger zone costs 300/cell, the pathfinder will literally route around the traps *by default*. 
- **Result:** The agent can survive and win the stage by simply issuing `AttackCoord Target`. The system will automatically avoid the traps for them. The model will never learn to use `DropRepellent`.

## Design Recommendations

### Option A: Refine the Terrain & Core Implementations (Recommended)

1. **Extend Zone Durations:**
   Update the `SetZoneModifier` handler in Rust (or its corresponding emission in Python) to last for at least **1500 ticks** (10 RL steps). This gives the swarm plenty of time to leverage the new flow field.

2. **Patch the Stage 3 Terrain:**
   In `macro-brain/src/training/curriculum.py`, the trap zones in Stage 3 (`_terrain_open_with_danger_zones`) must be set to `hard_cost = 100` (normal pathable ground) but visually demarcated (perhaps using `soft_cost = 40`).
   *Rationale:* This makes the straightest route straight through the trap. The agent MUST explicitly cast `DropRepellent` (adds +200 cost) to push the local terrain over the threshold, creating the barrier themselves. 

3. **Persistent Navigation `SwarmEnv`:** 
   Update `macro-brain/src/env/actions.py` so that casting a tactical ability (like Pheromone or Repellent) caches and rebroadcasts the factions's last known `AttackCoord` directive to prevent them from stopping when using skills.

### Option B: Keep Current Stage 3, Introduce Hidden Traps (Not Recommended)
We could leave the terrain at cost 300, but make the traps invisible. However, this conflates Fog-of-War (Stage 4) mechanics with Stage 3 goals, violating the "One new skill per stage" curriculum principle.

### Recommended Option: A
Fixes the root causes directly and mathematically compels the agent to use the target abilities.

## Reward Calculation Re-Alignment

Currently, `rewards.py` uses a zero-sum reward function: Terminal Win/Loss plus small kill/death drips and time penalties. 

**Recommendation:** DO NOT add dense or proximity-based rewards for using these items.
- *Why no dense tracking?* If we re-add Euclidean `approach_scale` (which appears stripped from the active `compute_shaped_reward`), the agent gets penalized for walking down the Stage 2 bottom detour path (since they aren't closing distance as fast).
- *Why no "+1 for casting"?* It leads to rapid button-mashing policies where the bot spins in circles casting pheromones without navigating.
- **Solution:** Standard terminal rewards are perfect. The environment organically kills agents that don't cast Pheromone (they run into the trap block) and those that don't cast Repellent (they walk through the trap). The surviving branches of the policy will inherently learn the association.

## Brute-Force Summary
- Stage 2 is brute-force proof.
- Stage 3 was highly exploitable but is fixed by Recommendation 2.

## Impact on Later Stages
These underlying core mechanical changes (duration of zone modifiers, persistence of motion commands) will directly resolve potential blocking issues when Stage 4 and Stage 5 require the model to perform highly dynamic routing updates.

## Finalized Solutions & Refinements

Based on review, the following refinements are integrated into the design strategy:

### Refinement 1: Solving "Action Spamming" Organically
Instead of explicitly blocking actions (which disrupts tactical combination steps), we rely on **Flow-Field Normalization**.
- **The Self-Correcting Mechanic:** If the AI spams `DropPheromone` continuously as it moves, it will cover the entire map in -50 cost zones. Since Dijkstra evaluates total path cost, if *every* cell is -50, the pathfinder mathematically defaults back to the physically shortest route. In Stage 2, that means routing straight through the Top Path trap and dying. 
- **Conclusion:** Spamming zones naturally neutralizes their advantage. The RL model will learn that precise, localized tactical drops are the only way to create pathing differentials without corrupting the map layout. No hard cooldowns required.

### Refinement 2: Radius Tweaking & Combat Attrition
Regarding whether the 60-unit radius is enough to block the path seamlessly:
- **The Combat Math Solution:** We don't need an airtight repulsor field. By sizing the actual target faction (the 60HP units they must kill to win) properly relative to the swarm's starting size, we can enforce **Attrition Checks**.
- **Mechanic:** Swarm units naturally spread out due to Boids separation logic. If the AI doesn't properly place a Repellent to route the *entire* swarm cleanly around the danger zone, the outer edges of the swarm will clip the trap's 25-unit combat radius. 
- **Result:** Those units will die. If the model allows 20-30% of its swarm to die by grazing the trap due to poor repellent placement, the surviving 70% will no longer have the DPS/HP required to defeat the final target. Strict math enforces precision.
