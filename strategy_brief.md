# Strategy Brief: Curriculum Integration of Heterogeneous Combat Dynamics

## Problem Statement
The micro-core architecture was recently updated to support complex heterogeneous combat mechanics: Area-of-Effect (AoE), Ray Penetration (Kinetic/Beam), Stat-Driven Mitigation (Armor), and Dynamic Ranges via `UnitClassId`. The current RL training curriculum (Stages 0-7) is structured around basic 1v1 pairwise DPS simulation and lacks scenarios that rigorously require or teach the swarm to counter these new advanced mechanics. We must determine if and how the existing training stages should be updated to exploit the new physics.

## Analysis

### 1. The "Frontal Charge" Problem
Prior to this update, a "frontal charge" was only discouraged by having a local numerical/DPS disadvantage. With the new `aoe` and `penetration` systems, spatial formation matters deeply.
- **AoE (Shapes & Falloff):** Punishes clumping. A tightly clustered swarm takes geometrically scaling damage.
- **Penetration: Beam:** Punishes linear approaches (chokepoints). It fires a ray that does not absorb energy, dealing full damage to every unit in the line.
- **Penetration: Kinetic:** Allows absorption body-blocking. Frontline units (with a high `absorption_stat`) can drain the ray's energy to protect fragile DPS units behind them.

### 2. Stage 5 (Forced Flanking) Re-evaluation
Currently, Stage 5 is "Blocked pending Rust Micro-Core upgrades for complex interactions." The goal is for the brain to use `SplitToCoord` to pincer an entrenched enemy because a frontal charge results in death. 
**Math check:** Without AoE/Penetration, a frontal charge mathematically operates identically to a pincer, because 1v1 pairwise combat only allows the front line to engage. In fact, splitting the swarm halves the local DPS at the point of contact, making flanking *strictly weaker* under pure 1v1 math!
**The solution:** By equipping the entrenched enemy with a **Penetration Beam** or an **AoE Polygon (Cone)** attack, a frontal charge in a chokepoint guarantees the entire swarm takes damage simultaneously. Flanking forces the enemy to turn the cone/beam toward only one sub-group, instantly cutting the incoming damage by 50-80%.

### 3. Stage 1 (Target Selection) Re-evaluation
Stage 1 requires picking the weak target (60 HP) before the Trap (200 HP). 
With stat-driven mitigation, the Trap can be equipped with `FlatReduction` or `PercentReduction` (e.g., 90% mitigation), making it mathematically invincible to the Brain's generic attack unless the debuff (which now triggers upon killing the soft target) bypasses mitigation or drastically drops the Trap's damage. The current Debuff drops Trap DPS to 25%. We can make the Trap infinitely more imposing visually and mathematically by using the new Armor mitigation, perfectly signaling "DO NOT ATTACK THIS YET."

### 4. Stage 7 (Protected Target) Update
Currently undefined. This is the perfect stage to teach **Screening/Absorption**. The target could be defended by long-range Penetration (Kinetic) turrets. The Brain would be given heterogeneous units (Tanks with high absorption, and fast squishy DPS). To reach the target, the flow field must inherently position the Tanks to absorb the kinetic ray energy, or the Brain must learn to route Tanks ahead using `AttackCoord`.

## Design Rationale

The curriculum mandate is "The General": every stage teaches one atomic skill. 
- The new math does not require *new* actions, but it provides the **physical reality** that makes the existing actions (`Split`, `AttackCoord` on specific paths) mathematically necessary rather than arbitrarily enforced. 
- If we do not implement the new weapons on enemies, the model can brute-force Stage 5 by just out-stating or clumping, entirely bypassing the need to split.

## Recommendations

### 1. Update Stage 5 (Forced Flanking) with Cone/Beam Enemy
- **Action:** Update the enemy in Stage 5 to use a class equipped with a `ConvexPolygon` (Cone) AoE weapon or a `Beam` Penetration weapon pointing down the V-shaped chokepoint. 
- **Rationale:** This mathematically guarantees that a unified frontal assault results in a catastrophic wipe. Only by using `SplitToCoord` to attack from two distinct angles (> 90 degrees apart) can the swarm minimize the geometric impact area of the enemy's attack.

### 2. Upgrade Stage 1 Trap to use Mitigation (Armor)
- **Action:** Swap the Stage 1 Trap's raw 200 HP advantage to a heavy `PercentReduction` mitigation (e.g., 80% damage reduction) but lower HP. 
- **Rationale:** High HP just means "takes longer to kill", whereas mitigation means "fundamentally ineffective to attack". It conceptually fits the idea of a "Trap" perfectly and utilizes the new mitigation system to solidify the lesson of Target Selection.

### 3. Define Stage 7 as "Screening" (Heterogeneous Swarm)
- **Action:** Introduce unit classes to the Brain's spawn in Stage 7 (e.g., 20 Tanks, 40 DPS). Give the enemy Kinetic Penetration weapons.
- **Rationale:** Requires the Brain to leverage the `absorption` math introduced with Kinetic penetration, forcing it to figure out how to absorb ray damage so the DPS units survive long enough to kill the Protected Target.

## Recommended Option

**Implement Recommendations 1 & 3 for future stages.** 
Since Stage 5 was explicitly blocked pending these engine upgrades, this mathematically unblocks Stage 5's design. Stage 7 has a clean slate to teach kinetic absorption. For Recommendation 2, determining if we should alter Stage 1 requires user feedback since Stage 1 training has already been reset and is currently active.

## Brute-Force Analysis

Without these updates (if Stage 5 used 1v1 combat), the Brain could easily brute-force the chokepoint. Because 1v1 combat means only units on the direct frontline take damage, 100 units in a line take the exact same damage as 10 units in a line. With AoE or Penetration, 100 units in a line take 10x the total damage. The new math definitively eliminates the frontal-charge brute-force vector.

## Impact on Later Stages
Stages 6 and 8 will naturally inherit these heterogeneous enemy attacks, making the endgame combat vastly more dynamic, requiring the model to identify unit classes and adapt its spatial formations (spread out for AoE, split/flank for beams).

## Open Questions for User
1. Since Stage 1 is currently training, do we want to hot-swap the Trap to use `PercentReduction` now to reinforce the lesson, or leave Stage 1 as-is (HP-based) and purely focus the advanced math on Stage 5+?
2. For Stage 5's entrenched enemy: Do you prefer an AoE Cone (punishes width of the frontal charge) or a Penetration Beam (punishes the depth/length of the frontal charge)?
