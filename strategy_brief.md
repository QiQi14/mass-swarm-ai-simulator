# Strategy Brief: Stage 1 Resumption Path Analysis

## Problem Statement
The user is evaluating the optimal checkpoint to resume training for Stage 1 (Target Selection) following critical fixes to the `Ch7` (Enemy Threat/ECP) data pipeline and the aggressive randomization of Y-axis spawns (which destroyed previous spatial memorization). The core question is whether to resume from the stalled Stage 1 checkpoint (`run_20260411_185052`, ~38% WR) or revert to the cleanly graduated Stage 0 checkpoint (`stage_0_graduated.zip`, 85% WR).

## Analysis
1. **The Argument for Stage 1 Checkpoint (~38% WR):** 
   Because `Ch7` elements were completely `0.0`, the specific convolutional filters mapped to `Ch7` received zero gradients during backpropagation. This preserves their random initialization, theoretically allowing them to ingest the new correct data cleanly without having collapsed.
   
2. **The Flaw (Spatial Overfitting):**
   While the `Ch7` filters are untouched, the *rest* of the network is not. To achieve a 38% WR without threat data and with static or semi-static coordinates, the Actor-Critic networks were forced to learn **spurious spatial correlations** (e.g., "always charge this specific center-right Y-coordinate"). 
   
3. **RL Unlearning Dynamics:**
   In Deep Reinforcement Learning (especially PPO), "unlearning" a heavily reinforced sub-optimal policy (a local optimum) requires massive entropy and can take significantly more gradient steps than learning on a fresh slate. Relying on the Stage 1 checkpoint means the model will suffer because its Actor head will output highly confident, but now entirely incorrect, actions for spatial shortcuts that are no longer valid due to the new aggressive Y-axis spawn randomization.

## Root Cause & Design Rationale
The 38% win-rate achieved in the previous Stage 1 run is a manifestation of an overfitted spatial heuristic, not a foundational mastery. The model survived by exploiting a vulnerability in the environment (static spawns) to bypass the missing Threat channel. 
Graduated Stage 0 (`stage_0_graduated.zip`), however, represents a mathematically pristine generalization of the `AttackCoord` primitive, completely free of the toxic spatial biases introduced during the flawed Stage 1 training session.

## Recommendations

### Option A: Resume from Stage 1 Checkpoint (`run_20260411_185052`)
- **Pros:** Preserves some minor specific adaptations to Stage 1's entity counts (50 vs 20 units).
- **Cons:** Model heavily penalizes itself early. Initial WR will likely crater from 38% to near 0%. The optimizer must spend thousands of steps lowering the probabilities of its memorized spatial shortcuts before the untouched `Ch7` filters can even begin establishing a robust correlation with the Target vs Trap selection logic.

### Option B: Start from Graduated Stage 0 (`stage_0_graduated.zip`)
- **Pros:** The model possesses a perfectly generalized `AttackCoord` primitive. There are no deeply embedded false correlations to "unlearn". The model immediately begins associating the newly functioning `Ch7` density with the correct `AttackCoord` action.
- **Cons:** A slight initial recalibration is needed as the model adjusts from Stage 0's 20-unit enemy groups to Stage 1's dual 50-unit groups, which is a negligible cost compared to unlearning bad habits.

## Recommended Option: Option B
**Start from Graduated Stage 0 checkpoint.**
It is demonstrably faster and mathematically smoother for a PPO agent to build complex behaviors (threat differentiation) atop a cleanly generalized foundation (Stage 0) than it is to aggressively destruct and rebuild a distorted, overfitted neural pathway (the broken Stage 1 run). 

## Brute-Force Analysis
With the Stage 1 environment now correctly randomizing the `Y-axis` for the Trap and Target, and the Trap (`50 units, 200 HP`) triggering a `Charge` when the debuff is applied, there is no spatial brute-force route available. The model must rely solely on the accurate mapping of `Ch1-6` (Density) and `Ch7` (Threat) to make a correct tactical decision.

## Impact on Later Stages
By establishing a genuine, learned correlation between Threat data and Target Selection (instead of patching over a spatial bias), we ensure the `TacticalExtractor` (CNN + MLP) builds a robust generalization. This is critical for Stage 2 (Pheromone Paths) and Stage 3 (Repellent Field), where accurate risk assessment and active avoidance are mandatory.

## Open Questions for User
- If we proceed with the Stage 0 checkpoint, should we delete the broken `run_20260411_185052` run directory to keep the training logs and artifacts pristine, or retain it for historical debugging purposes?
