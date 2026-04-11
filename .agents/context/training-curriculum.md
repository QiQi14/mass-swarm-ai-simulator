# Training Curriculum Reference (v3.1)

> **Audience:** All agents working on training, curriculum stages, rewards, or bot behavior.
> **Binding keywords:** `curriculum`, `stage`, `training`, `spawn`, `terrain`, `fog`, `debuff`, `graduation`

> [!IMPORTANT]
> Read `engine-mechanics.md` first for how combat, terrain, buffs, and movement work in the Rust core.
> This document covers the Python-side training curriculum that uses those mechanics.

---

## 1. Design Principle: "The General"

> The model is a General, not a state machine picker.

- Every action is an **atomic primitive** (see `conventions.md`)
- Complex tactics (flank, lure, retreat-and-ambush) must **emerge** from the model composing primitives
- Stages teach ONE new skill each, then the model combines them in later stages
- If a stage can be brute-forced (won without using the intended skill), the stage is poorly designed

---

## 2. Stage Summary

| Stage | Name | New Action | Fog | Key Mechanic |
|-------|------|-----------|-----|-------------|
| 0 | 1v1 Navigation | Hold, AttackCoord | OFF | Find and kill single target |
| 1 | Target Selection | — | OFF | Pick weak target over strong trap |
| 2 | Pheromone Path | DropPheromone | OFF | Route through safe path via pheromone |
| 3 | Repellent Field | DropRepellent | OFF | Push swarm away from danger zones |
| 4 | Fog Scouting | Scout | **ON** | Find hidden targets with recon |
| 5 | Flanking | SplitToCoord, MergeBack | ON | Pincer attack from two angles |
| 6 | Full Tactics | Retreat | ON | All 8 actions, combine primitives |
| 7 | Protected Target | — | ON | Full tactics vs guarded HVT |
| 8 | Randomized | — | ON | Random scenario from pool |

### Graduation Requirements

Each stage requires sustained win rate (rolling window) + minimum episodes:

| Stage | Win Rate | Min Episodes | Extra |
|-------|----------|-------------|-------|
| 0 | 85% | 30 | — |
| 1 | 80% | 50 | — |
| 2 | 80% | 50 | — |
| 3 | 80% | 50 | — |
| 4 | 80% | 50 | — |
| 5 | 80% | 50 | avg_flanking_score ≥ 0.3 |
| 6 | 80% | 50 | — |
| 7 | 75% | 100 | — |
| 8 | 80% | 500 | — |

---

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

### Stage 4: Fog Scouting (800×800) — NEEDS REDESIGN
- **Fog:** ON (first stage with fog)
- **Brain:** 50 units, center of map
- **Target:** At random edge (hidden by fog)
- **New action:** Scout (split 10% recon to coordinate)
- **Goal:** Scout → find target → AttackCoord → kill
- **Planned enhancement:** Add retargeting objective (multi-target or patrol target)

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

## 4. Key Files

| File | Responsibility |
|------|---------------|
| `macro-brain/src/training/curriculum.py` | Stage configs, spawn generators, terrain generators |
| `macro-brain/src/env/swarm_env.py` | Action unlock schedule, debuff logic, win/loss detection |
| `macro-brain/src/env/bot_controller.py` | Bot AI (HoldPosition, Charge, Patrol, debuff-aware charging) |
| `macro-brain/src/training/callbacks.py` | Graduation logic, episode logging |
| `macro-brain/profiles/tactical_curriculum.json` | Master profile (factions, combat rules, rewards, stage descriptions) |

---

## 5. Bot Behavior System

**File:** `macro-brain/src/env/bot_controller.py`

Bot factions (trap, target, patrol) are controlled by Python heuristics, NOT by the RL model.

### Strategies

| Strategy | Behavior |
|----------|----------|
| `HoldPosition` | Stay at spawn (sends `Idle`). Switches to `Charge` if debuff is applied. |
| `Charge` | Navigate toward target faction each step |
| `Patrol` | Alternate between waypoint list (with threshold proximity check) |
| `Adaptive` | Charge when healthy, retreat when losing (with hysteresis) |
| `Mixed` | Randomly pick one strategy per episode (anti-memorization) |

### Debuff-Aware Behavior

When Python's `_apply_trap_debuff()` fires in SwarmEnv:
1. `ActivateBuff` directive sent to Rust (reduces trap damage to 25%)
2. Trap's `BotController._debuff_applied = True`
3. On next `compute_directive()`, HoldPosition strategy detects flag → switches to `Charge`
4. Trap charges toward brain faction → guarantees engagement without brain retargeting

---

## 6. Reward Structure

**File:** `macro-brain/src/env/rewards.py`

| Component | Value | Purpose |
|-----------|-------|---------|
| `time_penalty_per_step` | -0.01 | Encourage speed |
| `kill_reward` | +0.05 per kill | Reward damage |
| `death_penalty` | -0.03 per death | Penalize losses |
| `win_terminal` | +10.0 | Victory bonus |
| `loss_terminal` | -10.0 | Defeat penalty |
| `survival_bonus_multiplier` | 5.0 | Bonus × surviving own units |
| `approach_scale` | 0.02 | Reward for closing distance to target |
| `exploration_reward` | 0.005 | Reward for exploring new fog cells |
| `threat_priority_bonus` | 2.0 | Bonus for engaging the correct target |
| `flanking_bonus_scale` | 0.1 | Bonus for angular separation in attacks |
| `debuff_bonus` | 2.0 | Bonus when debuff fires (target killed first) |

---

## 7. Episode Flow

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

## 8. Common Pitfalls & Gotchas

> [!CAUTION]
> **HP buff is inert.** Buff modifiers on stat_index 0 (HP) are stored but never read.
> To reduce enemy HP, use combat damage (interaction rules), not buff multipliers.
> See `engine-mechanics.md` Section 3.

> [!WARNING]
> **Terrain default cost is 100, not 0.** Sending all-zero terrain makes every cell "free" 
> for pathfinding, which breaks cost comparisons. Always use 100 as baseline.

> [!WARNING]
> **get_spawns_for_stage() returns a TUPLE**, not a list.
> Format: `(spawns_list, role_meta_dict)` where role_meta has `trap_faction` and `target_faction`.

> [!NOTE]
> **Episode length:** `max_steps=500` in profile, but `FrameSkipWrapper(skip=5)` means
> `500/5 = 100` outer steps. Each outer step = 5 × 30 = 150 simulation ticks.
> Total episode = 15,000 ticks = 250 sim-seconds at 60 TPS.
