# Curriculum Stages

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

### Stage 2: Pheromone Path (600×600)
- **Brain:** 50 units, 100 HP
- **Trap:** 40 units, 200 HP, HoldPosition on the fast (top) path
- **Target:** 20 units, 60 HP, HoldPosition at right side
- **Terrain:** Two-path map with wall band through center
  - Top path: fast (cost 100) but trap group blocks it
  - Bottom path: slow (mud, soft_cost 40) but safe
  - Wall: permanent (65535) with gap at x=2-5
- **Goal:** Use DropPheromone on bottom path to attract swarm through safe route
- **New action:** DropPheromone (cost modifier -50, attracts flow field)

### Stage 3: Repellent Field (600×600)
- **Brain:** 50 units, 100 HP, spawns at left edge
- **Traps:** 2-3 groups of 20 units, 200 HP, scattered in danger zones
- **Target:** 20 units, 60 HP, right edge
- **Terrain:** Open field with danger zones at NORMAL cost (hard_cost 100, soft_cost 40 visual markers). Flow field routes THROUGH traps by default. Agent must DropRepellent (+200) to create avoidance zones.
- **Goal:** Use DropRepellent on danger zones to push swarm away from trap engagements
- **New action:** DropRepellent (cost modifier +200, repels flow field)
- **Trap count randomized:** 2-3 groups to prevent memorization

### Stage 4: Fog Scouting (800×800)
- **Fog:** ON (first stage with fog)
- **Brain:** 50 units, center of map
- **Targets:** Target A and Target B spawn at opposite edges (hidden by fog)
- **New action:** Scout (split 10% recon to coordinate)
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