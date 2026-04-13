# Strategy Brief: Complete Curriculum Redesign (v5.0)

## Problem Statement

The training curriculum (Stages 0–8) was last designed when the Rust Micro-Core supported only basic 1v1 pairwise combat with homogeneous units. Since then, the engine has received **five major upgrades** that fundamentally expand what the simulation can express:

1. **Heterogeneous Unit Classes** — `UnitClassId`, class-filtered `InteractionRule`, dynamic `range_stat_index`
2. **Stat-Driven Mitigation** — `PercentReduction` and `FlatReduction` on target stats (armor)
3. **Per-Entity Cooldowns** — `CooldownTracker` resource for burst/artillery-style weapons
4. **AoE Damage** — Circle, Ellipse, ConvexPolygon shapes with Linear/Quadratic falloff
5. **Penetration Damage** — Kinetic (absorbed by frontline) and Beam (full damage through line)
6. **Boids 2.0 Tactical Steering** — 10 Hz sharded sensor with Kite and PeelForAlly subsumption behaviors, per-class engagement range hold, `UnitTypeRegistry`
7. **Observation Channel v4.0** — 8-channel CNN (count + ECP density per faction, terrain, fog, ch6-ch7 reserved)

The old curriculum does not use **any** of these features. Stages 5–8 were marked as "blocked pending Micro-Core upgrades" — those upgrades are now complete. We must redesign the entire curriculum from scratch to exploit this new physics.

## Analysis

### 1. Inventory of Engine Capabilities vs. Curriculum Usage

| Engine Feature | Implemented | Used in ANY Stage | Gap |
|---|:---:|:---:|---|
| 1v1 pairwise combat | ✅ | ✅ (all stages) | — |
| Debuff (damage multiplier) | ✅ | ✅ (Stage 1) | — |
| Zone modifiers (Pheromone/Repellent) | ✅ | ✅ (Stages 2-3) | — |
| Fog of War + LKP buffer | ✅ | ✅ (Stage 4) | — |
| Split/Merge sub-factions | ✅ | ⚠️ (Stage 5 skeleton) | No physics that REQUIRES it |
| UnitClassId (heterogeneous spawns) | ✅ | ❌ | Never used in any spawn |
| Dynamic combat range (stat-driven) | ✅ | ❌ | Never configured in profile |
| Stat-driven mitigation (armor) | ✅ | ❌ | Never configured in profile |
| Per-entity cooldowns | ✅ | ❌ | Never configured in profile |
| AoE (Circle/Polygon/Falloff) | ✅ | ❌ | Never configured in profile |
| Penetration (Kinetic/Beam) | ✅ | ❌ | Never configured in profile |
| Boids 2.0 Kite behavior | ✅ | ❌ | Never configured in unit_types |
| Boids 2.0 PeelForAlly behavior | ✅ | ❌ | Never configured in unit_types |
| Engagement range hold | ✅ | ❌ | Never configured in unit_types |
| ch6 (Interactable terrain) | ✅ plumbed | ❌ | Always zeros |
| ch7 (System objective signal) | ✅ plumbed | ⚠️ (Stage 4 intel ping) | Only Stage 4 |

**Conclusion:** 11 out of 17 engine capabilities are completely unused by the curriculum. The model graduates knowing only basic movement, target selection, pheromone/repellent, fog scouting, and splitting — with no exposure to the spatial formation pressure that AoE/Penetration creates, no heterogeneous army composition, and no counter-play to ranged/armored enemies.

### 2. The "Frontal Charge Still Works" Problem

Under pure 1v1 pairwise combat (current profile), a ball of 50 units is tactically identical to 5 separate groups of 10. Only the nearest source-target pairs deal damage each tick. This means:

- **Flanking is mathematically pointless** — splitting your army halves your local DPS at each contact point without reducing incoming damage.
- **Formation doesn't matter** — clumped or spread, same DPS throughput.
- **The model will learn: "always ball up and rush"** — because it literally IS the optimal strategy under current physics.

With AoE and Penetration active on enemies:
- **Clumping is catastrophic** — AoE with Linear falloff hits every unit in the zone; Beam penetration hits every unit in the line.
- **Flanking becomes mathematically required** — splitting forces the enemy AoE/beam to choose ONE sub-group, halving total damage intake.
- **Formation matters deeply** — Kinetic penetration rewards "body-blocking" with Tanks in front.

### 3. The "Correct Curriculum Pyramid"

Each stage should teach exactly ONE atomic skill. The new skills enabled by engine upgrades are:

| Skill | Engine Feature Required | Prerequisite Skills |
|---|---|---|
| **Spread formation** | AoE on enemy | Basic navigation |
| **Flanking** | AoE/Beam on entrenched enemy | Split/Merge + Spread |
| **Body-blocking / Screening** | Kinetic penetration + heterogeneous units | Flanking + unit awareness |
| **Kiting / Range management** | Engagement range hold + Kite behavior | Basic navigation |
| **Target prioritization under pressure** | Armored enemies + burst weapons | Target selection |

### 4. Combat Math for New Stage Designs

#### Base Reference (current profile)
```
Brain: 50 units × 100 HP, DPS = 25/unit → 1,250 total DPS
Range: 25 world units (melee)

Enemies vary by stage.
Episode = 100 outer steps = 15,000 ticks = 250 sim-seconds at 60 TPS
```

#### Stage 5: Entrenched Defender with AoE Cone

```
Enemy: 30 units × 200 HP, DPS = 25/unit, HoldPosition
       + AoE ConvexPolygon (60° cone, range 80, damage -15/s, Linear falloff)

Frontal charge scenario (brain clumped):
  Brain enters cone → all 50 units take 15 DPS × 30 sources = 450 DPS splash
  + Standard 1v1 melee: ~30 sources × 25 = 750 DPS
  Total incoming: ~1,200 DPS against brain's 5,000 total HP
  Time to wipe brain: ~4.2s
  Brain DPS on enemy: 50 × 25 = 1,250 against 6,000 HP
  Time to kill enemy: ~4.8s → BRAIN LOSES (dies first)

Flanking scenario (brain splits 50/50 from two 90°+ angles):
  Each sub-group: 25 units → only one group in the cone at a time
  AoE damage to one group: 15 × 30 × falloff ≈ 225 DPS on 25 units
  Other group takes ZERO AoE → free DPS
  Combined brain DPS: still 1,250 on 6,000 HP
  Effective incoming: ~975 DPS (AoE halved + only one side in melee)
  → BRAIN WINS with ~30 survivors
```

**Verdict:** Flanking is mathematically required. ✅ Frontal charge loses. ✅

#### Stage 7: Kinetic Penetration + Heterogeneous Brain

```
Enemy turrets: 10 units, Kinetic penetration weapon
  base_energy: 200, ray_width: 3.0, damage: -30/s, cooldown: 60 ticks
  Fires a ray that hits every unit in a line, absorbed per target

Brain composition:
  Class 0 (Infantry): 30 × 80 HP, range 15, DPS 25
  Class 1 (Tank): 20 × 300 HP, absorption_stat: stat[4]=0.8

Protected Target: 10 units × 60 HP, HoldPosition behind turrets

Without body-blocking:
  Kinetic ray hits infantry in front → 200 energy ÷ 80 HP = 2.5 infantry killed per shot
  10 turrets × 1 shot/sec = 25 infantry killed in 10 seconds → brain wipe

With Tanks screening in front:
  Tank absorbs: 300 HP × 0.8 absorption = 240 energy absorbed per tank
  Ray exhausted on first tank → infantry behind takes ZERO damage
  Tanks survive ~12 seconds (200 energy × 10 turrets ÷ 300 HP)
  Infantry free DPS window: 12 seconds of clean damage on target
  → BRAIN WINS with most infantry alive
```

**Verdict:** Screening is mathematically required. ✅

## Design Rationale

### Curriculum Philosophy: "The General" + Physics-Enforced Learning

The previous curriculum relied on **artificial failure states** (e.g., trap with 200 HP you "shouldn't" attack). The new curriculum uses **physics** to make the intended strategy mathematically optimal:

- Stage 5 doesn't say "don't rush" — an AoE cone **kills you** if you rush.
- Stage 7 doesn't say "put tanks in front" — kinetic penetration **kills your DPS** if tanks aren't blocking.

No artificial penalties, no reward engineering tricks. The physics IS the teacher.

### Principles for the Redesign

1. **One skill per stage** — never overload.
2. **Physics, not rewards** — the engine mechanics must make the correct strategy strictly numerically superior.
3. **Brute-force impossible** — verify via combat math that "ball up and rush" fails.
4. **Progressive complexity** — each new feature builds on skills from prior stages.
5. **Exploit every engine feature** — every implemented Rust system should appear in at least one stage.
6. **Observation channels must be useful** — ch6 and ch7 should carry meaningful signal by the time they're needed.

## Recommendations: Complete 9-Stage Curriculum (v5.0)

### Stage 0: Navigation (KEEP — no changes)
- **Skill:** Move to coordinate
- **World:** 400², 20² grid, fog OFF
- **Brain:** 40 × 100 HP (generic)
- **Enemy:** 20 × 60 HP, HoldPosition
- **Actions:** Hold, AttackCoord
- **Why unchanged:** Foundational. The model learns that `AttackCoord → kill → win`.
- **Graduation:** 85% WR / 30 episodes

---

### Stage 1: Target Selection (KEEP — no changes)
- **Skill:** Read ECP density to pick correct target
- **World:** 500², 25² grid, fog OFF
- **Brain:** 50 × 100 HP
- **Trap:** 50 × 200 HP, HoldPosition
- **Target:** 50 × 24 HP, HoldPosition
- **Debuff:** Killing target first → trap DPS × 0.25 + trap charges
- **Actions:** Hold, AttackCoord
- **Why unchanged:** Stage 1 works well. The HP-vs-ECP signal is clear. Replacing the trap's raw HP with armor mitigation is an option but unnecessary — the current design already forces correct target selection with its HP asymmetry.
- **Graduation:** 80% WR / 50 episodes

---

### Stage 2: Pheromone Path (KEEP — no changes)
- **Skill:** Use zone modifier to redirect pathfinding
- **World:** 600², 30² grid, fog OFF
- **Brain:** 50 × 100 HP
- **Trap:** 40 × 200 HP on the fast path
- **Target:** 20 × 60 HP on the far side
- **Terrain:** Two-path wall map
- **Actions:** +DropPheromone
- **Why unchanged:** Zone modifier mastery is prerequisite for Stage 3.
- **Graduation:** 80% WR / 50 episodes

---

### Stage 3: Repellent Field (KEEP — no changes)
- **Skill:** Create avoidance zones around danger areas
- **World:** 600², 30² grid, fog OFF
- **Brain:** 50 × 100 HP
- **Traps:** 2-3 groups of 15 × 200 HP in danger zones
- **Target:** 20 × 60 HP at far edge
- **Terrain:** Open field with hard_cost=100 danger zones (flow field ignores them)
- **Actions:** +DropRepellent
- **Why unchanged:** Repellent mastery is prerequisite for later stages with terrain-based objectives.
- **Graduation:** 80% WR / 50 episodes

---

### Stage 4: Fog Scouting (KEEP — minor refinement only)
- **Skill:** Scout under fog, sequential retargeting
- **World:** 800², 40² grid, fog ON
- **Brain:** 50 × 100 HP, center
- **Targets:** 2 groups (15 × 60 HP each) at random edges
- **ch7:** Decaying Intel Ping toward active objective
- **Actions:** +Scout
- **Why essentially unchanged:** This stage teaches fog-of-war navigation and scouting. The ch7 intel ping system is already implemented. No combat mechanic changes needed.
- **Graduation:** 80% WR / 50 episodes

---

### Stage 5: Forced Flanking — AoE Cone Enemy ← **NEW DESIGN**
- **Skill:** Use SplitToCoord to attack from multiple angles simultaneously
- **World:** 800², 40² grid, fog ON
- **Brain:** 60 × 100 HP, spawns at left edge
- **Enemy:** 30 × 200 HP, HoldPosition at V-shaped chokepoint center
  - **NEW: AoE weapon** — ConvexPolygon (60° forward cone), range 80, damage -15/s per source, Linear falloff, TargetAligned rotation
  - Standard 1v1 melee: 25 DPS, range 25
- **Terrain:** V-shaped permanent walls (65535) creating a chokepoint opening toward the brain
- **Actions:** +SplitToCoord, +MergeBack
- **Combat math:** See §4 above — frontal charge = death, flanking pincer = win with ~30 survivors
- **Brute-force check:** ❌ Frontal charge loses to AoE cone. Single-mass attack gets wiped. Only SplitToCoord from 90°+ angles survives.
- **Configuration additions:**
  - New InteractionRule with `aoe.shape: ConvexPolygon` (triangle vertices forming 60° cone)
  - `aoe.falloff: Linear` (units at edge of cone take less damage)
  - Enemy using class_id with `source_class` filter on the AoE rule
- **Graduation:** 80% WR / 50 episodes, avg_flanking_score ≥ 0.3

---

### Stage 6: Spread Formation — AoE Circle Enemy ← **NEW DESIGN**
- **Skill:** Learn to spread units to minimize AoE splash damage, use Retreat to reposition
- **World:** 1000², 50² grid, fog ON
- **Brain:** 60 × 100 HP
- **Enemy:** 40 × 150 HP, Charge behavior, **NEW: AoE Circle weapon** (radius 30, damage -10/s, Quadratic falloff)
  - Standard 1v1 melee: 20 DPS, range 25
- **Terrain:** Open field
- **Actions:** +Retreat (all 8 actions now unlocked)
- **Key lesson:** The enemy **charges** the brain. If the brain clumps up, AoE circle splash devastates the entire force. The brain must learn to:
  1. Spread units using DropRepellent on its own position (creative use of repellent)
  2. Retreat from engagement to reset formation
  3. Re-engage from spread positions
- **Combat math:**
  ```
  Clumped brain (all 60 in radius 30 zone):
    AoE: 40 enemies × 10 DPS × 60 targets = 24,000 effective DPS
    → Brain wiped in < 1 second

  Spread brain (groups of ~10 across 6 positions):
    AoE per group: 40 × 10 × ~3 targets (Quadratic falloff) = 1,200 DPS
    → Each group survives ~5 seconds, total brain lasts ~30 seconds
    → Brain DPS: 60 × 20 = 1,200 vs enemy 6,000 HP → kills in 5s
    → BRAIN WINS with ~40 survivors
  ```
- **Brute-force check:** ❌ Ball-rush dies instantly to AoE. Must spread.
- **Graduation:** 80% WR / 50 episodes

---

### Stage 7: Screening — Kinetic Penetration + Heterogeneous Army ← **NEW DESIGN**
- **Skill:** Body-block with Tanks to protect fragile DPS units; manage heterogeneous force
- **World:** 1000², 50² grid, fog ON
- **Brain heterogeneous:**
  - Class 0 (Infantry): 35 × 80 HP, range 15, DPS 25
  - Class 1 (Tank): 15 × 300 HP, stat[4]=0.8 (absorption), range 15, DPS 10
- **Enemy turrets:** 10 × 200 HP, HoldPosition
  - **NEW: Kinetic Penetration weapon** — ray_width 3.0, base_energy 200, absorption_stat_index 4, damage -30/s, cooldown 60 ticks
- **Protected Target (HVT):** 10 × 60 HP, HoldPosition behind turrets
- **Terrain:** Open approach, turrets at 2/3 distance, HVT behind turrets
- **Actions:** All 8
- **Key lesson:** Kinetic penetration rays kill entire columns of Infantry. But Tanks with high `absorption_stat` drain ray energy, shielding Infantry behind them. The brain must route Tanks ahead of Infantry.
- **Unit type definitions required:**
  ```json
  "unit_types": [
    {
      "class_id": 0,
      "stats": [{"index": 0, "value": 80.0}],
      "engagement_range": 0.0
    },
    {
      "class_id": 1,
      "stats": [{"index": 0, "value": 300.0}, {"index": 4, "value": 0.8}],
      "engagement_range": 0.0,
      "movement": { "max_speed": 40.0 }
    }
  ]
  ```
- **Combat math:** See §4 above — unscreened approach = infantry wiped, tanks-first approach = clean win
- **Brute-force check:** ❌ Generic rush kills all infantry before reaching target. Must screen.
- **Graduation:** 75% WR / 100 episodes

---

### Stage 8: Randomized Graduation ← **EXPANDED**
- **Skill:** Generalize across ALL mechanics
- **World:** Variable (selected from stage pool)
- **Design:** Each episode randomly selects from Stages 1–7 configs (including the new AoE/Penetration stages)
- **Actions:** All 8
- **Purpose:** Prove the model can handle any combination of: target selection, terrain navigation, fog scouting, flanking, spread formation, and screening — without knowing which scenario it faces.
- **Graduation:** 80% WR / 500 episodes

## Profile Configuration Changes Required

The current `tactical_curriculum.json` only has 4 InteractionRules (basic bidirectional melee between factions 0↔1 and 0↔2). The new curriculum requires:

1. **Stage 5 AoE rule:** Enemy cone weapon (ConvexPolygon shape, Linear falloff, source_class filter)
2. **Stage 6 AoE rule:** Enemy circle splash (Circle shape, Quadratic falloff)
3. **Stage 7 Penetration rule:** Enemy kinetic turret (Kinetic energy model, absorption_stat_index, cooldown)
4. **Stage 7 unit_types:** Tank and Infantry class definitions with different stats, speeds, and absorption values
5. **Stage 7 mitigation rule:** For turret defense (PercentReduction on class 1 absorption stat)

These can be stage-specific combat rule overrides (sent in the reset payload), or new rules added to the base profile with class filters ensuring they only activate with the correct unit compositions.

## Brute-Force Analysis Summary

| Stage | Can "ball up and rush" win? | Why not? |
|:---:|:---:|---|
| 0 | ✅ Yes (intended) | No counter needed — pure navigation |
| 1 | ❌ No | Trap has 10× total HP; dies if wrong target |
| 2 | ❌ No | Trap group blocks the fast path; detour required |
| 3 | ❌ No | Traps on direct path; repellent required |
| 4 | ❌ No | Targets hidden by fog; scouting required |
| 5 | ❌ No | **AoE cone wipes clumped frontal charge** |
| 6 | ❌ No | **AoE circle wipes clumped formation** |
| 7 | ❌ No | **Kinetic penetration kills unscreened infantry** |
| 8 | ❌ No | Random — must handle all scenarios |

## Impact on Later Stages

This is the **final** curriculum design. Stage 8 (randomized) is the capstone that validates generalization. Beyond Stage 8, the model graduates and the training curriculum is complete. Future work (Phase 4+) focuses on scaling to 10K entities and WASM/ONNX export — not new curriculum stages.

## Implementation Complexity Assessment

| Stage | Rust Changes | Python Changes | Profile Changes | Difficulty |
|:---:|:---:|:---:|:---:|:---:|
| 0-4 | None | None | None | ✅ Already working |
| 5 | None (AoE system exists) | Spawn generators, terrain (V-walls) | AoE InteractionRule, stage-specific rules | 🟡 Medium |
| 6 | None (AoE system exists) | Spawn generators, reward tuning | AoE InteractionRule | 🟡 Medium |
| 7 | None (Penetration + UnitType exists) | Spawn generators, heterogeneous spawns | Kinetic rule, unit_types, class stats | 🔴 Hard |
| 8 | None | Update stage pool to include new stages | None | 🟢 Easy |

**Key insight:** All Rust engine code is already implemented. The implementation work is entirely in:
1. Python spawn generators (new unit compositions, positions)
2. Python terrain generators (V-wall for Stage 5)
3. Profile/reset payload configuration (new InteractionRules with AoE/penetration configs, unit_types)
4. Bot behavior configuration (new strategies for stages 5-7)

## Open Questions for User

1. **Stage 5 map size:** The current skeleton uses 800×800. Should we keep this or expand to 1000×1000 for more flanking room? (800 seems sufficient for the V-wall chokepoint design.)

2. **Stage 6 ordering:** Stage 6 currently teaches "all tactics + retreat" but I've redesigned it as "spread formation." The retreat skill naturally emerges from needing to reposition away from AoE splash. Should we keep retreat as the explicit new action unlock here, or move it earlier?

3. **Stage 7 heterogeneous spawns:** The brain currently only spawns homogeneous units. Stage 7 introduces 2 unit classes for the brain. Should we add an earlier stage (e.g., Stage 6.5) that introduces heterogeneous units WITHOUT the screening requirement, just to let the model acclimate to multi-class armies?

4. **Profile structure:** Should stage-specific InteractionRules be embedded in the master profile and keyed by stage, or should each stage send its own custom combat rules in the reset payload? (The latter is more flexible but requires Python changes to construct stage-specific rule sets.)

5. **ch6/ch7 activation:** Should ch6 (interactable terrain) become active in any stage? Currently it's always zeros. One option: ch6 = "allied sub-faction density" (separate from ch0 which merges all friendlies), giving the model awareness of where its split groups are. This would naturally support flanking geometry in Stage 5+.
