# Curriculum Stages

## 2. Action Vocabulary & Stage Unlocks (v3)

The simulation uses a 3-dimension action encoding: `[action, coord, modifier]`.
*   **0. Hold** (Stage 0)
*   **1. AttackCoord** (Stage 0)
*   **2. ZoneModifier** (Stage 2) — merged from DropPheromone/DropRepellent
*   **3. SplitToCoord** (Stage 5)
*   **4. MergeBack** (Stage 5)
*   **5. SetPlaystyle** (Stage 5)
*   **6. ActivateSkill** (Stage 7)
*   **7. Retreat** (Stage 6)

*Note: Scout has been removed from the action vocabulary.*

## 3. Stage Details

### Stage 0: 1v1 Navigation (500×500)
- **Brain:** 50 units, 100 HP each
- **Enemy:** 1 group (20 units, 60 HP)
- **Terrain:** Flat
- **Goal:** Learn AttackCoord → navigate to enemy → kill
- **Win condition:** All enemies dead

### Stage 1: Target Selection (500×500)
- **Brain:** 50 units, 100 HP, spawns at left side (80, random Y: 200-300)
- **Trap:** 50 units, 200 HP, HoldPosition (right side, random Y)
- **Target:** 50 units, 60 HP, HoldPosition (right side, random Y)
- **Terrain:** Flat, trap/target separated by ≥200 vertical units to avoid overlap
- **Faction randomization:** 50% chance trap=faction 1, target=faction 2 (or vice versa)
- **Goal:** Read density observations, AttackCoord the weaker target
- **Debuff mechanic:** Killing target first → trap DPS × 0.25 + trap enrages (charges brain)
- **Win condition:** All enemies dead (brain must kill debuffed trap after target)

> [!WARNING]
> **Brute-force check:** Brain CANNOT kill 50×200HP trap head-on (brain dies first).
> Target selection is MANDATORY — there is no brute-force path.
> After debuff, trap charges the brain (bot controller switches HoldPosition → Charge).
> This eliminates the need for retargeting — the fight comes to the brain.

### Stage 2: Pheromone Fortress (600×600)
- **Brain:** 50 units, 100 HP, spawns at left edge (80, random Y: 200-400)
- **Rangers (target):** 20 units, 60 HP, HoldPosition INSIDE walled fortress
  - Extended-range combat rule: range 150, -12 DPS (via `stage_combat_rules.py`)
- **Tanks (trap):** 40 units, 200 HP, HoldPosition at Path A (clean entry)
  - Standard melee: range 25, -25 DPS
- **Terrain:** Fortress enclosure (grid 16-26, Y 9-21) with 2 openings on left wall
  - Path A (clean, hard_cost=100): Tanks block this shortest entry
  - Path B (mud, soft_cost=40): Safe but slow — requires pheromone to route through
  - Seed controls which opening is A vs B (randomized per episode)
- **Goal:** Use ZoneModifier on Path B to route swarm through mud, kill squishy rangers first, then pivot to fight tanks alone
- **New action:** ZoneModifier (modifier 0: attracts flow field)
- **Kill-order enforcement:** Fighting tanks first = -25/s melee + -12/s ranged = overwhelmed. Killing rangers first removes crossfire → tanks alone are beatable.
- **No debuff mechanic** — the ranger/tank DPS asymmetry IS the mechanic
- **Win condition:** All enemies dead (both rangers AND tanks)

### Stage 3: Repellent Field (600×600)
- **Brain:** 50 units, 100 HP, spawns at left edge
- **Traps:** 2-3 groups of 20 units, 200 HP, scattered in danger zones
- **Target:** 20 units, 60 HP, right edge
- **Terrain:** Open field with danger zones at NORMAL cost (hard_cost 100, soft_cost 40 visual markers). Flow field routes THROUGH traps by default. Agent must use ZoneModifier (+200) to create avoidance zones.
- **Goal:** Use ZoneModifier on danger zones to push swarm away from trap engagements
- **New action:** ZoneModifier (modifier 1: repels flow field)
- **Trap count randomized:** 2-3 groups to prevent memorization

### Stage 4: Fog Scouting (800×800)
- **Fog:** ON (first stage with fog)
- **Brain:** 50 units, center of map
- **Targets:** Target A and Target B spawn at opposite edges (hidden by fog)
- **Strategy:** Scout using standard unit splitting to coordinate
- **Mechanics:** `ch7` provides a decaying "Intel Ping" representing an active objective. Once Target A is eliminated, it automatically switches to Target B.
- **Goal:** Follow decaying Intel Pings, explore fog, eliminate Target A, retarget and eliminate Target B.

### Stage 5: Forced Flanking (1000×1000)
- **New actions:** SplitToCoord (30%), MergeBack
- **Terrain:** Strong "V" shaped forward-facing wall or extreme hazard swamp.
- **Goal:** Enemy is entrenched in the chokepoint. Brain MUST split into two groups to hit the enemy from both open sides simultaneously, as a frontal generic charge will result in death.
- **Status:** Designed. Blocked pending Rust Micro-Core upgrades for complex interactions.

### Stage 6: The Lure & Ambush (1000×1000)
- **New action:** Retreat
- **Spawns:** Brain Bait (10) at center, Brain Army (80) hidden at corner, Enemy (100) charging at Bait.
- **Goal:** Survive. Brain MUST use Retreat to kite the massive enemy army across the map and drag them into the hidden Brain Army to win via a counter-attack.
- **Status:** Designed. Blocked pending visualizer and core architecture upgrades.

### Stage 7: Protected Target (1000×1000)
- **Patrol bots with waypoints**
- **Goal:** Navigate past patrols to reach guarded HVT
- **Status:** Not yet redesigned for v3.1 curriculum

### Stage 8: Randomized
- Picks random stage config from pool
- Final validation stage

---

## 8. Episode Flow

```
SwarmEnv.reset():
  1. Get stage config → spawn positions, terrain, fog settings
  2. Send reset payload to Rust via ZMQ
  3. Receive initial state snapshot
  4. Initialize LKP buffer, bot controllers
  
SwarmEnv.step(action):
  1. Convert MultiDiscrete action → directive(s)
  2. Inject pending debuff if any
  3. Compute bot directives (one per bot faction)  
  4. Send batch payload to Rust
  5. Receive new snapshot
  6. Check win/loss/timeout
  7. Check if target killed → apply debuff
  8. Compute reward
  9. Return (obs, reward, done, truncated, info)
```

---