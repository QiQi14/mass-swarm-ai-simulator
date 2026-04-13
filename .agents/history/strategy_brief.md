# Strategy Brief: Curriculum Learnability & Stage 4 Refactor post-Channel Update

## Problem Statement
The recent refactoring of the 8 observable channels explicitly separated count density (`ch0`, `ch1`) from Effective Combat Power density (`ch2`, `ch3`), re-allocating `ch7` as an empty "System Objective Signal." We need to analyze whether the Stage 0 through 4 curriculum requires refactoring to accommodate or leverage this new observation space architecture.

## Analysis

### 1. Stages 0 to 3: The Impact of Explicit ECP Channels
**Diagnosis: Vastly Improved Learnability. No Refactoring Needed.**
- Previously, in Stage 1, the Trap (50 bots, 200 HP) and the Target (50 bots, 60 HP) looked identical in `ch1` (Count Density) because they both had 50 headcount. The agent experienced a 50% "coin-flip" plateau because it lacked the sensory input to distinguish them.
- With the explicit implementation of `ch3` (Enemy ECP Density), the Threat is now visually distinct in the observation tensor from Step 1. The Trap registers a massive 10,000 ECP hotspot in `ch3`, while the Target registers a modest 3,000 ECP.
- For Stages 2 & 3, the agent now easily associates massive ECP spikes in `ch3` with danger, providing a crystal clear visual prompt to execute `DropPheromone` or `DropRepellent` (manipulating `ch4` traversal cost).
- **Combat Math & Balance:** The Rust core systems were already computing combat symmetrically. Pluming the ECP logic up to the RL Brain purely solves the perception bottleneck without needing to alter bot stats or win-conditions.

### 2. Stage 4: Fog Scouting & Retargeting
**Diagnosis: Sparse Reward Gradient. Refactoring Required.**
- Stage 4 introduces Fog of War (`fog_enabled: true`). Outside of visible cells, `ch1` and `ch3` are completely masked (`0.0`).
- The agent currently spawns in an 800×800 grid completely blind. Relying on the agent to randomly stumble onto an enemy at the map's edge constitutes an impossible, sparse RL gradient.
- The newly freed `ch7` (System Objective Signal) provides the exact tool required to bridge this gap. Training the agent to hunt down "Intel Pings" prepares it for dynamic objectives in Stages 5+.

## Design Rationale

Stage 4 must teach the agent to traverse a fog-covered map by following intel objectives, coordinate an attack, and **explicitly retarget** across the map when an objective changes. Using `ch7` as an "Intel Radar Ping" enables sequential objective tracking without bypassing the fog mechanics.

## Recommendations

### Refactor Stage 4 (Objective-Driven Intel Recon)
We must implement the Python-side logic to drive `ch7`.

1. **Map Design & Spawns:** 800×800 (40×40 Grid), `fog_enabled: true`. 
   - Brain: 50 units (100 HP) at map center.
   - Target A: 15 units (60 HP) at random edge.
   - Target B: 15 units (60 HP) at an *opposite* random edge.

2. **Sequential Intels (Drive `ch7`):**
   - The Python `vectorizer.py` evaluates the Active Objective coordinate.
   - Modify the `ch7` channel to render a dense blob (e.g., 3x3 cells) precisely at Target A's centroid.
   - Once Target A is eliminated (`faction_count == 0`), the environment immediately updates `ch7` to ping Target B's centroid. Only ONE target is highlighted at a time.

3. **Behavioral Loop Imparted:**
   - The RL Brain cannot see `ch1/ch3` (blocked by fog), but DOES see `ch7`.
   - The Brain learns: `ch7` is heavily correlated with future rewards. It moves forces (`AttackCoord` or `Scout`) to the `ch7` ping.
   - Upon arriving, fog clears, `ch5` registers 1.0, and `ch1/ch3` illuminate -> Combat engages.
   - Once cleared, `ch7` vanishes and reappears miles away, forcing the Brain to learn **retargeting** to complete the episode.

## Brute-Force Check
1. **Can the agent wait?** No, the `-0.01` time penalty will force action.
2. **Can it brute-force the map sweep?** No, 800x800 is too large to manually sweep within the step limit with a dense swarm. 
3. **Does this teach the intended skill?** Yes, it definitively links the `ch7` tensor logic to map navigation under Fog, and enforces retargeting.

## Impact on Later Stages
- Training the model to interpret `ch7` as an objective vector is highly scalable. In Stage 6/7, `ch7` can be used to denote HVT locations or extraction points. 

## Open Questions for User
- **Precision of Intel:** Should `ch7` render as a sharp 3x3 grid point (exact coordinate), or should it be a wide, blurred Gaussian heatmap? A blurred heatmap explicitly forces the agent to use the `Scout` action to find the precise location *within* the blob before moving the slower main army.
