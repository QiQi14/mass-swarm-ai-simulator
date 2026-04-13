# Mathematics of the Mass-Swarm AI Simulator

> **Purpose:** Complete mathematical specification of every formula in the simulation engine.
> All notation is context-agnostic — the engine assigns no semantic meaning to stat indices.

---

## Table of Contents

1. [Stat Model](#1-stat-model)
2. [Damage Delivery — Pairwise (1v1)](#2-damage-delivery--pairwise-1v1)
3. [Damage Delivery — Area-of-Effect (AoE)](#3-damage-delivery--area-of-effect-aoe)
4. [Damage Delivery — Penetration (Ray)](#4-damage-delivery--penetration-ray)
5. [Damage Delivery — Composability](#5-damage-delivery--composability)
6. [Mitigation Functions](#6-mitigation-functions)
7. [Buff / Debuff Multipliers](#7-buff--debuff-multipliers)
8. [Removal Conditions](#8-removal-conditions)
9. [Movement Physics](#9-movement-physics)
10. [Terrain & Pathfinding Costs](#10-terrain--pathfinding-costs)
11. [Observation Space — Density Maps](#11-observation-space--density-maps)
12. [Observation Space — ECP Density](#12-observation-space--ecp-density)
13. [Observation Space — Channels & Summary](#13-observation-space--channels--summary)
14. [Fog of War](#14-fog-of-war)
15. [Neural Architecture](#15-neural-architecture)
16. [Reward Function](#16-reward-function)
17. [Graduation Criteria](#17-graduation-criteria)

---

## 1. Stat Model

Each entity stores a flat array of `f32` values:

```
S = [s₀, s₁, ..., s₇]    where sᵢ ∈ ℝ, |S| = 8
```

The engine assigns **no semantic meaning** to any index. Meaning is injected by the game profile at runtime.

| Symbol | Definition |
|--------|-----------|
| `S[i]` | Value of stat slot `i` on an entity |
| `F` | Faction identifier (`u32`) |
| `C` | Unit class identifier (`u32`, default 0) |
| `P = (x, y)` | World-space position |
| `V = (dx, dy)` | Velocity vector |

---

## 2. Damage Delivery — Pairwise (1v1)

**System:** `interaction_system`  
**Condition:** Rule has `aoe = None` AND `penetration = None`

Each source entity damages only the **single nearest valid target** per rule per tick.

### Target Selection

For source entity `s` with position `Pₛ`, the target is:

```
t* = argmin   ‖Pₜ − Pₛ‖²
     t ∈ T(r)
```

where `T(r)` is the set of valid targets:

```
T(r) = { t :  Fₜ = r.target_faction
           ∧  Cₜ matches r.target_class (if set)
           ∧  aggro_allowed(r.source_faction, r.target_faction)
           ∧  cooldown_ready(s, r)
           ∧  ‖Pₜ − Pₛ‖ ≤ R_eff }
```

### Effective Range

```
R_eff = S_s[r.range_stat_index]   if r.range_stat_index is set
      = r.range                    otherwise
```

### Per-Tick Delta

```
Δt = 1/60                                              (tick duration)
μ  = get_multiplier(Fₛ, id_s, combat_damage_stat)      (buff factor, default 1.0)
δ_base = r.delta_per_second × Δt × μ                   (base per-tick delta)
δ_final = mitigate(δ_base, r, t*)                       (see §6)

S_t*[r.stat_index] += δ_final
```

### Timing Modes

**Mode A — Continuous** (`cooldown_ticks = None`):  
Effect applies every tick while in range.

**Mode B — Cooldown-Gated** (`cooldown_ticks = N`):  
After firing, entity is blocked for N ticks. Effective averaged rate:

```
rate_avg = |r.delta_per_second| / (60 × N)    per tick
```

---

## 3. Damage Delivery — Area-of-Effect (AoE)

**System:** `aoe_interaction_system`  
**Condition:** Rule has `aoe = Some(...)` AND `penetration = None`

### Algorithm

1. **Find impact:** `I = nearest_valid_target(s, r)` → position `(Iₓ, Iᵧ)`
2. **Compute rotation:** `θ = atan2(Iᵧ − Pₛᵧ, Iₓ − Pₛₓ)` (or `θ = r.aoe.fixed_angle`)
3. **Query splash zone:** All entities within `bounding_radius(shape)` of `I`
4. **For each candidate `t`:**
   - Transform to shape-local coordinates (centered on `I`, rotated by `−θ`)
   - Hit-test → `d_norm ∈ [0, 1]` or reject
   - Apply `damage × falloff(d_norm)`

### Local Coordinate Transform

```
dx = Pₜₓ − Iₓ
dy = Pₜᵧ − Iᵧ

local_x =  dx·cos(θ) + dy·sin(θ)
local_y = −dx·sin(θ) + dy·cos(θ)
```

### Shape Hit-Test Functions

**Circle** (radius `r`):
```
d² = local_x² + local_y²
Hit iff d² ≤ r²
d_norm = √(d²) / r
```

**Ellipse** (semi-major `a`, semi-minor `b`):
```
e = (local_x / a)² + (local_y / b)²
Hit iff e ≤ 1
d_norm = √e
```

**Convex Polygon** (≤ 6 vertices, CCW winding):

Uses O(V) half-plane gradient math. For each edge `AᵢBᵢ`:

```
nₓᵢ = Bᵧᵢ − Aᵧᵢ          (inward normal x-component)
nᵧᵢ = Aₓᵢ − Bₓᵢ          (inward normal y-component)
cᵢ  = Aₓᵢ · Bᵧᵢ − Aᵧᵢ · Bₓᵢ    (half-plane constant)
```

**Hit-test + gradient:**
```
rᵢ = (P · nᵢ) / cᵢ = (Pₓ · nₓᵢ + Pᵧ · nᵧᵢ) / cᵢ

d_norm = max_i(rᵢ)

Hit iff d_norm ≤ 1.0
```

`d_norm = 0` at center, `d_norm = 1` at edge. This produces correct gradients for all convex shapes, including thin cones where the naive `dist/max_vertex_dist` would be geometrically incorrect at lateral boundaries.

> **Degenerate edge guard:** If `|cᵢ| < ε`, store `1/cᵢ = 0` to avoid division-by-zero. This occurs when a vertex is at the polygon origin.

### Falloff Functions

Given `d_norm = d ∈ [0, 1]`:

| Falloff | Factor `f(d)` | Character |
|---------|--------------|-----------|
| None | `1.0` | Uniform — grenade |
| Linear | `max(0, 1 − d)` | Linear dropoff |
| Quadratic | `max(0, 1 − d²)` | Steep center, gentle edge |

### Damage Application

```
δ_splash = δ_base × mitigate(1, r, t) × f(d_norm)
S_t[r.stat_index] += δ_splash
```

### Bounding Radius

For spatial grid query optimization:

| Shape | Bounding Radius |
|-------|----------------|
| Circle | `r` |
| Ellipse | `max(a, b)` |
| Polygon | `max_i(‖vᵢ‖)` |

---

## 4. Damage Delivery — Penetration (Ray)

**System:** `penetration_interaction_system`  
**Condition:** Rule has `penetration = Some(...)`

### Algorithm

1. **Find impact:** `I = nearest_valid_target(s, r)` → position `(Iₓ, Iᵧ)`
2. **Build ray direction:**
   ```
   D = I − Pₛ
   L = ‖D‖
   d̂ = D / L
   ```
3. **Guard:** If `L < ε`, skip (Correction #3: division-by-zero)
4. **Filter candidates** by perpendicular distance
5. **Sort** by distance along ray
6. **Sequential energy delivery** with absorption

### Ray Candidate Filtering (Correction #2: 2D Cross-Product)

For candidate at position `Pₜ`:

```
AP = Pₜ − Pₛ

dot_along = AP · d̂ = APₓ · d̂ₓ + APᵧ · d̂ᵧ        (signed distance along ray)
cross     = APₓ · d̂ᵧ − APᵧ · d̂ₓ                   (2D cross product)
perp_dist = |cross|                                   (perpendicular distance)
```

**Hit criteria (pen-only mode):**
```
dot_along > 0                (in front of source)
dot_along ≤ R_eff            (within weapon range)
perp_dist ≤ ray_width        (within ray thickness)
```

> **Why cross-product, not trig?** The 2D cross product `|A × B| = |A| |B| sin(θ)` gives perpendicular distance directly. Since `d̂` is unit length, `|cross| = |AP| sin(θ) = perp_dist`. No trigonometric functions needed.

### Energy Model (Correction #4: Kinetic vs Beam)

Remaining energy `E ∈ [0, 1]`, initialized to `1.0`.

**Kinetic** (burst damage):
```
For each target in sorted order:
    damage_delivered = δ_base × E × falloff_factor
    S_t[stat_index] += damage_delivered

    // Absorption
    absorbed = min(E, S_t[absorption_stat] / base_energy)
    E ← E − absorbed

    if E ≤ 0 → break
```

**Beam** (sustained drain):
```
For each target in sorted order:
    damage_delivered = δ_base × E × falloff_factor
    S_t[stat_index] += damage_delivered

    // No absorption — E stays at 1.0
```

### Range-Based Falloff (pen-only mode)

```
d_fraction = dot_along / R_eff
falloff_factor = max(0, 1 − d_fraction)
```

### Normalized Energy

Energy is normalized to `[0, 1]` to prevent floating-point cascading errors:

```
absorbed = min(E_remaining, target_stat / base_energy)
```

The `min` clamp ensures energy never goes negative. Using the ratio `target_stat / base_energy` keeps absorption proportional regardless of damage magnitude.

---

## 5. Damage Delivery — Composability

When a rule has **both** `aoe` and `penetration`, the systems compose:

| Aspect | Provider |
|--------|----------|
| **Spatial filter** (which targets are hit) | AoE shape |
| **Damage scaling** (gradient within zone) | AoE falloff |
| **Energy budget** (sequential absorption) | Penetration energy model |
| **Target ordering** (who gets hit first) | Penetration ray sort |

### Composite Algorithm

```
1. Find impact I = nearest_target(s, r)
2. Build ray: d̂ = normalize(I − Pₛ)
3. For each candidate:
    a. Transform to AoE-local coordinates (centered on I, rotated by θ)
    b. AoE shape hit-test → reject if outside shape
    c. Compute dot_along (distance along ray)
    d. Reject if dot_along < 0 or > R_eff
4. Sort remaining candidates by dot_along
5. Sequential energy delivery:
    For each target:
        aoe_factor = aoe.falloff(d_norm)
        damage = δ_base × E × aoe_factor
        S_t[stat_index] += damage
        E -= absorption (if Kinetic)
```

### Example: Cone-Shaped Shotgun

```json
{
  "aoe": {
    "shape": {
      "type": "ConvexPolygon",
      "vertices": [[-1,0], [30,-15], [30,15]],
      "rotation_mode": "TargetAligned"
    },
    "falloff": "None"
  },
  "penetration": {
    "ray_width": 0,
    "energy_model": { "Kinetic": { "base_energy": 100.0 } },
    "absorption_stat_index": 0
  }
}
```

Result: Targets within the cone shape are hit, ordered by distance along the ray. First target absorbs energy proportional to its stat, reducing damage for targets behind.

---

## 6. Mitigation Functions

Applied to `δ_base` before delivery. Optional per-rule via `mitigation` config.

### Percent Reduction

```
δ_final = δ_base × (1 − clamp(S_t[mit.stat_index], 0, 1))
```

Example: `mit_value = 0.5` → 50% damage reduction.

### Flat Reduction

```
δ_final = sign(δ_base) × max(0, |δ_base| − S_t[mit.stat_index] × Δt)
```

Example: `mit_value = 300, Δt = 1/60` → absorbs 5.0 damage per tick.

---

## 7. Buff / Debuff Multipliers

### Modifier Types

| Type | Formula |
|------|---------|
| `Multiplier` | `effective = base × value` |
| `FlatAdd` | `effective = base + value` |

### Multiplier Query

```
get_multiplier(faction, entity_id, stat_index) =
    ∏ { m.value : m ∈ active_modifiers
                  where m.stat_index == stat_index
                  and m.type == Multiplier
                  and buff.targets_entity(entity_id) }

Default: 1.0 (when no modifiers match)
```

### Entity Targeting

```
targets = None       → dormant (no effect)
targets = Some([])   → ALL entities in faction
targets = Some([1,5]) → only entities 1 and 5
```

---

## 8. Removal Conditions

Each removal rule defines a threshold condition on a stat slot:

```
For each entity, for each removal rule r:
    if r.condition == LessOrEqual:
        remove iff S[r.stat_index] ≤ r.threshold
    if r.condition == GreaterOrEqual:
        remove iff S[r.stat_index] ≥ r.threshold
```

---

## 9. Movement Physics (Boids 2.0)

### Per-Entity Pipeline (each tick)

```
Δt = 1/60

// 1. Macro direction (60 Hz)
macro_dir = flow_field.sample(P) or normalize(waypoint − P)

// 2. Boids separation (60 Hz)
separation = Σ { (P − Pₙ) / ‖P − Pₙ‖²  :  ‖P − Pₙ‖ ≤ separation_radius }

// 3. Tactical direction (10 Hz, entity-sharded)
// Written by tactical_sensor_system: subsumption winner from Kite/PeelForAlly
tactical_dir = TacticalState.direction
tactical_weight = TacticalState.weight

// 4. Engagement range hold
// If entity has engagement_range > 0 and enemy within range, suppress flow
if engagement_range > 0 AND ∃ enemy: ‖P_enemy − P‖ ≤ engagement_range:
    w_flow_eff = 0          // Hold position at range
else:
    w_flow_eff = w_flow      // Normal flow following

// 5. 3-vector blend & steer
desired = normalize(macro_dir × w_flow_eff + separation × w_sep + tactical_dir × tactical_weight) × v_max
V ← lerp(V, desired, steering_factor × Δt)

// 6. Wall collision (axis-independent)
P_next = P + V × Δt
if terrain.hard_cost(P_next.x, P.y) = 65535:  V.x = 0; P_next.x = P.x
if terrain.hard_cost(P.x, P_next.y) = 65535:  V.y = 0; P_next.y = P.y

// 7. Speed cap (soft terrain + buff)
soft_mod = terrain.soft_cost(cell) / 100
speed_mult = get_multiplier(F, id, movement_speed_stat)
v_eff = v_max × soft_mod × speed_mult

if ‖V‖ > v_eff:
    V ← V × (v_eff / ‖V‖)

// 8. Boundary clamp
P = clamp(P_next, [0,0], [W, H])
```

### Tactical Sensor (10 Hz)

```
// Entity sharding: process 1/6th of entities per tick
if entity.index % 6 ≠ tick % 6: skip

// Subsumption: highest-weight behavior wins exclusively
best = (ZERO, 0.0)
for behavior in UnitTypeDef.behaviors:
    (dir, weight) = evaluate(behavior, entity, grid)
    if weight > best.weight:
        best = (dir, weight)

TacticalState.direction = best.dir
TacticalState.weight = best.weight
```

### Behavior Evaluation

**Kite** (flee from enemy):
```
nearest_enemy = argmin { ‖P_e − P‖ : F_e ≠ F, ‖P_e − P‖ ≤ trigger_radius }
dir = normalize(P − P_nearest_enemy)     // flee direction
```

**PeelForAlly** (rush to distressed ally):
```
nearest_ally = argmin { ‖P_a − P‖ : F_a = F, C_a = target_class,
                        tick − CombatState_a.last_damaged_tick < 30 }
dir = normalize(P_nearest_ally − P)       // rush direction
```

### Movement Parameters

| Symbol | Default | Purpose |
|--------|---------|---------|
| `v_max` | 60.0 | Base speed (units/sec) |
| `steering_factor` | 5.0 | Velocity lerp rate |
| `separation_radius` | 6.0 | Boids repulsion range |
| `w_sep` | 1.5 | Separation weight |
| `w_flow` | 1.0 | Flow field weight (dynamically suppressed by engagement range) |
| `engagement_range` | 0.0 | Range at which W_flow → 0 (0 = melee, no suppression) |
| `tactical_weight` | 0.0–3.0 | Sensor output (behavior-dependent) |

---

## 10. Terrain & Pathfinding Costs

### Dual-Cost Model

```
hard_cost ∈ {100, 300, 65535}    → pathfinding + wall collision
soft_cost ∈ [0, 65535]           → movement speed modifier only
```

### Pathfinding Cost

```
cost(cell) = hard_cost(cell) + Σ zone_modifier(cell)
```

### Movement Speed

```
movement_modifier = soft_cost(cell) / 100
effective_speed = v_max × movement_modifier × speed_mult
```

### Zone Modifiers

```
Pheromone: cost_modifier = −50   → cost = 50   → preferred path
Repellent: cost_modifier = +200  → cost = 300  → avoided path
Duration:  zone_modifier_duration_ticks (default 1500 ≈ 25s)
```

---

## 11. Observation Space — Density Maps

### Entity Count Density (ch0, ch1)

```
For each entity (x, y, faction):
    cx = ⌊x / cell_size⌋
    cy = ⌊y / cell_size⌋
    if 0 ≤ cx < W and 0 ≤ cy < H:
        count[faction][cy · W + cx] += 1

normalized = min(count / max_density, 1)    where max_density = 50
```

Out-of-bounds entities are skipped (not clamped).

---

## 12. Observation Space — ECP Density

### Effective Combat Power (ch2, ch3)

```
For each entity (x, y, faction, stat, damage_mult):
    cx = clamp(⌊x / cell_size⌋, 0, W−1)      ← CLAMPED, not skipped
    cy = clamp(⌊y / cell_size⌋, 0, H−1)

    ecp = max(S[ecp_stat_index] × damage_mult, 1.0)
    ecp_grid[faction][cy · W + cx] += ecp

// Normalization
max_ecp_cell = max_density × max_entity_ecp
normalized = min(ecp_grid[cell] / max_ecp_cell, 1)
```

Where `ecp_stat_index` is configurable (default: 0) and `max_entity_ecp` is auto-computed from spawn stats each episode.

---

## 13. Observation Space — Channels & Summary

### 8 Spatial Channels (50 × 50)

| Ch | Content | Normalization | Pad |
|----|---------|---------------|-----|
| 0 | Friendly count | `count / 50` | 0 |
| 1 | Enemy count (merged) | `count / 50` | 0 |
| 2 | Friendly ECP | `ecp / max_ecp_cell` | 0 |
| 3 | Enemy ECP (merged) | `ecp / max_ecp_cell` | 0 |
| 4 | Terrain cost | `hard_cost / 65535` | 1 |
| 5 | Fog awareness | 3-level merge | 1 |
| 6 | Interactable terrain | reserved | 0 |
| 7 | System objective | `intensity × decay(d)` | 0 |

### Map Padding

```
pad_x = (50 − W) / 2
pad_y = (50 − H) / 2
active → channels[pad_y:pad_y+H, pad_x:pad_x+W]
```

### 12-Dimensional Summary Vector

| Idx | Content | Formula | Range |
|-----|---------|---------|-------|
| 0 | Own alive | `min(count / 10000, 1)` | [0,1] |
| 1 | Enemy alive | `min(count / 10000, 1)` | [0,1] |
| 2 | Own avg stat[k] | `min(avg / max_stat, 1)` | [0,1] |
| 3 | Enemy avg stat[k] | `min(avg / max_stat, 1)` | [0,1] |
| 4 | Sub-factions | `min(n / 5, 1)` | [0,1] |
| 5 | Own total stat[k] | `min(count × avg / (10000 × max_stat), 1)` | [0,1] |
| 6 | Enemy total stat[k] | scaled similarly | [0,1] |
| 7 | Time elapsed | `min(step / max_steps, 1)` | [0,1] |
| 8 | Fog explored % | `mean(ch5[active] > 0.3)` | [0,1] |
| 9 | Has sub-factions | `float(subs > 0)` | {0,1} |
| 10 | Intervention | `float(active)` | {0,1} |
| 11 | Force ratio | `own / (own + enemy)` | [0,1] |

Where `k = summary_stat_index` (configurable, default 0, derived from removal rules).

---

## 14. Fog of War

### 3-Level Merge

```
fog(cell) = 1.0    if visible(cell)           ← currently in line of sight
          = 0.5    if explored(cell)           ← seen before, now hidden
          = 0.0    otherwise                   ← never seen
```

### Last Known Position (LKP) Cache

```
For enemy channels (ch1, ch3):
    if fog(cell) > 0.9:    lkp[cell] = live_data[cell]
    else:                  output[cell] = lkp[cell]       ← stale
```

---

## 15. Neural Architecture

### TacticalExtractor

```
Input: 8 × (50 × 50) grids + 12-dim summary

CNN:  Conv2d(8→32, k=5, s=2, p=2) → ReLU
      Conv2d(32→64, k=3, s=2, p=1) → ReLU
      Flatten → Linear(→128) → ReLU → 128-dim

MLP:  Linear(12→64) → ReLU → Linear(64→64) → ReLU → 64-dim

Combiner: Concat(128+64) → Linear(192→256) → ReLU → Actor + Critic
```

### Action Space

```
MultiDiscrete([8, 2500])

Component 0: [Hold, AttackCoord, Pheromone, Repellent, Split, Merge, Retreat, Scout]
Component 1: flat coordinate → grid_x = val % 50, grid_y = val // 50
```

---

## 16. Reward Function

### Per-Step

```
reward = 0

// Time pressure
reward += time_penalty                          (−0.01)

// Combat trading (count-based)
reward += enemies_killed × kill_reward           (+0.05 each)
reward += own_lost × death_penalty               (−0.03 each)

// Terminal
Win:     reward += win_terminal + survival_bonus × (survivors / initial)
                  = 10.0 + 5.0 × ratio
Loss:    reward += loss_terminal                 (−10.0)
Timeout: reward += loss_terminal                 (−10.0)
```

### Gradient Guarantee

```
Clean Win  ≈ +12 to +15
Bloody Win ≈  +5 to +10
Timeout    ≈ −12 to −14
Loss       ≈ −11 to −13
```

### Flanking Score

```
v₁ = enemy_centroid − brain_centroid
v₂ = enemy_centroid − sub_centroid
α  = arccos(v₁ · v₂ / (‖v₁‖ ‖v₂‖)) × (180/π)
flanking_score = min(α / 180, 1)
```

0° = same-side, 180° = perfect pincer. Anti-exploit: sub must be within 15 cells of enemy.

---

## 17. Graduation Criteria

```
Rolling window: 200 episodes
Win rate = wins / 200

Each episode:
    if win_rate ≥ target AND episode == WIN AND extra_met:
        streak += 1
    else:
        streak = 0

    if streak ≥ required → GRADUATE
```

| Stage | Win Rate | Streak | Extra |
|-------|----------|--------|-------|
| 0 | 85% | 50 | — |
| 1–6 | 80% | 50 | — |
| 5 | 80% | 50 | avg_flank > 0.3 |
| 7 | 75% | 50 | — |
| 8 | 80% | 500 | — |
