# Micro-Core Engine Mechanics Reference

> **Audience:** All agents modifying training, curriculum, bot behavior, or anything touching simulation logic.
> **Binding keywords:** `combat`, `damage`, `buff`, `debuff`, `terrain`, `movement`, `flow field`, `removal`, `stat`, `HP`, `DPS`, `pheromone`, `repellent`

> [!IMPORTANT]
> Rust Micro-Core is **context-agnostic**. It has ZERO knowledge of what "HP" or "damage" means.
> All game semantics are injected at runtime via the **GameProfile JSON contract**.
> The engine only knows: stat indices, interaction rules, removal rules, terrain costs, buffs, and navigation targets.

---

## 1. Entity Model

Every entity has:
- **`FactionId(u32)`** — which faction it belongs to (0 = brain, 1/2 = bots)
- **`StatBlock([f32; 8])`** — 8 abstract stat slots. Meaning is defined by game profile:
  - `stat[0]` = HP (by convention in tactical_curriculum.json)
  - `stat[1]` = Movement speed modifier slot (optional)
  - `stat[2]` = Combat damage modifier slot (optional)
  - `stat[3..7]` = Unused / reserved
- **`Position { x, y }`** — world coordinates
- **`Velocity { dx, dy }`** — current movement vector
- **`EntityId { id: u32 }`** — unique entity identifier

### Unit Classes

Entities carry a `UnitClassId(u32)` component. Default: 0 (generic).

The engine is **context-agnostic** — it doesn't know what class 0 or class 1 means.
The game profile defines the mapping (e.g., class 0 = "Infantry", class 1 = "Sniper").

UnitClassId is used by `InteractionRule` for class-specific combat targeting:
- `source_class: Option<u32>` — only fire from entities of this class
- `target_class: Option<u32>` — only hit entities of this class
- When `None`, the rule matches any class (backward compatible)

**Key files:** `micro-core/src/components/`

---

## 2. Combat System (Interaction)

**File:** `micro-core/src/systems/interaction.rs`

### How Damage Works

Combat is rule-driven. Each `InteractionRule` defines:
```json
{
  "source_faction": 1,
  "target_faction": 0,
  "range": 25.0,
  "effects": [{ "stat_index": 0, "delta_per_second": -25.0 }]
}
```

**Per-tick calculation (line-by-line):**
```
For each source entity in source_faction:
  damage_mult = get_multiplier(source_faction, entity_id, combat_damage_stat)
  For each neighbor in range (spatial grid query):
    If neighbor is in target_faction:
      stat_block[effect.stat_index] += delta_per_second * (1/60) * damage_mult
```

### Critical Details

1. **`damage_mult`** comes from `FactionBuffs.get_multiplier()` using the `combat_damage_stat` index from the profile. If no buff is active, `damage_mult = 1.0`.
2. **Damage is PER-ENTITY, PER-TICK.** Each source entity within range applies its own damage to each target entity. This means 50 units in range deal 50× the damage.
3. **`delta_per_second` is FIXED in the interaction rule** — it does NOT read from any stat on the source entity. The only modifier is the buff multiplier.
4. **Combat is symmetric by rules:** you need TWO rules for bidirectional combat (A→B and B→A).
5. **AggroMask** can disable specific faction-pair combat (used by flanking/split mechanics).

### DPS Calculation

```
Effective DPS per unit = |delta_per_second| * damage_mult
Total faction DPS = num_units_in_range × effective_DPS_per_unit
Time to kill = target_total_HP / attacker_total_DPS
```

**Example (tactical_curriculum.json):**
- delta_per_second = -25.0, combat range = 25 units
- Brain 50 units, each dealing 25 DPS → 1,250 total DPS
- Trap 50 units × 200 HP = 10,000 total HP
- Time to kill trap = 10,000 / 1,250 = 8 seconds

### Dynamic Range

InteractionRules can use a stat from the source entity as the combat range:
- `range_stat_index: Option<usize>` — if set, `range = source.StatBlock[idx]`
- Falls back to the fixed `range` field if stat is missing
- Use case: Snipers (class with high stat[3]=200.0) vs Infantry (stat[3]=15.0)

### Stat-Driven Mitigation

InteractionRules can specify target-side damage mitigation:
- `mitigation.stat_index` — which stat on the TARGET provides mitigation
- `mitigation.mode`:
  - `PercentReduction`: `damage = base * (1.0 - target_stat.clamp(0..1))`
  - `FlatReduction`: `damage = (base.abs() - target_stat).max(0) * base.signum()`
- Use case: Tanks (stat[4]=0.5 → 50% damage reduction)

### Interaction Cooldowns

InteractionRules can have per-entity cooldowns:
- `cooldown_ticks: Option<u32>` — after firing, entity waits N ticks before firing again
- Tracked by `CooldownTracker` resource (keyed by entity_id + rule_index)
- Cleared on environment reset
- Use case: Heavy artillery (fires every 120 ticks = 2 seconds)

### Example: Heterogeneous Combat

Given game profile:
- Class 0 (Infantry): HP=100, Range=15, no mitigation
- Class 1 (Sniper): HP=40, Range(stat[3])=200, cooldown=120 ticks
- Class 2 (Tank): HP=300, Armor(stat[4])=0.5 (50% reduction)

Rules:
1. Infantry→Any: range=15, damage=-10/s, no class filter
2. Sniper→Any: range_stat=3, damage=-50/s, cooldown=120, source_class=1
3. Any→Tank: range=15, damage=-10/s, mitigation={stat:4, mode:PercentReduction}

Result: Sniper hits from 200 units away, deals 50 damage burst every 2 sec.
Tank takes 50% less damage from everything. Infantry is baseline.

---

## 3. Buff / Debuff System

**Files:** `micro-core/src/config/buff.rs`, `micro-core/src/systems/directive_executor/buff_tick.rs`

### How Buffs Are Applied

Buffs are stored per-faction in `FactionBuffs.buffs: HashMap<u32, Vec<ActiveBuffGroup>>`.
Each `ActiveBuffGroup` contains:
- `modifiers: Vec<ActiveModifier>` — list of `(stat_index, modifier_type, value)`
- `remaining_ticks: u32` — countdown to expiry
- `targets: Option<Vec<u32>>` — entity targeting:
  - `None` → dormant (no effect)
  - `Some([])` → ALL entities in faction
  - `Some([1, 2, 3])` → specific entity IDs only

### What Buffs Actually Affect

Buffs **DO NOT directly modify StatBlock values**. Instead, they provide multipliers that systems query:

| System | Queries | Buff Effect |
|--------|---------|-------------|
| `interaction.rs` (combat) | `get_multiplier(faction, entity, combat_damage_stat)` | Scales damage OUTPUT of the faction |
| `movement.rs` | `get_multiplier(faction, entity, movement_speed_stat)` | Scales movement speed |

> [!CAUTION]
> **HP buff is a NO-OP.** A `Multiplier` modifier on `stat_index: 0` (HP) is stored but **NEVER READ by any system**.
> No system calls `get_multiplier(faction, entity, 0)`.
> To reduce HP, you must use interaction rules (combat damage), not buff multipliers.
> The `stat_index: 0` modifier in `activate_buff` only provides a **signal** to Python — the engine ignores it.

### Buff Lifecycle

1. Python sends `ActivateBuff` directive → Rust stores in `FactionBuffs`
2. Each tick, `buff_tick_system` decrements `remaining_ticks`
3. When ticks reach 0, the group is removed
4. After removal, a **cooldown** starts (`buff_cooldown_ticks` from config)
5. During cooldown, new `ActivateBuff` for that faction is **silently rejected**

### Current Profile Config (tactical_curriculum.json)

```json
"abilities": {
  "buff_cooldown_ticks": 180,
  "movement_speed_stat": 1,
  "combat_damage_stat": 2,
  "activate_buff": {
    "modifiers": [
      { "stat_index": 0, "modifier_type": "Multiplier", "value": 0.25 },
      { "stat_index": 2, "modifier_type": "Multiplier", "value": 0.25 }
    ],
    "duration_ticks": 9999
  }
}
```

**Effective result when debuff fires on trap:**
- stat_index 0 (HP) × 0.25 → **NO EFFECT** (nothing reads HP multiplier)
- stat_index 2 (damage) × 0.25 → Trap damage output reduced to 25%
- Duration: 9999 ticks ≈ 166 seconds (effectively permanent for the episode)

---

## 4. Entity Removal System

**File:** `micro-core/src/systems/removal.rs`

Entities are removed when their stat value meets a threshold:
```json
"removal_rules": [
  { "stat_index": 0, "threshold": 0.0, "condition": "LessOrEqual" }
]
```
This means: when `stat_block[0] <= 0.0`, despawn the entity.

The removal system runs after the interaction system each tick.

---

## 5. Terrain System

**File:** `micro-core/src/terrain.rs`

Terrain is a 2D grid of costs, used by the flow field pathfinder to compute optimal movement paths.

### Two Cost Layers

| Layer | Purpose | Used By |
|-------|---------|---------|
| `hard_costs: Vec<u32>` | Pathfinding obstacles | Flow field (Dijkstra) — higher cost = harder to path through |
| `soft_costs: Vec<u32>` | Movement speed modifiers | Movement system — affects entity speed on that cell |

### Cost Tiers (from profile thresholds)

```json
"terrain_thresholds": {
  "impassable_threshold": 65535,
  "destructible_min": 60001
}
```

| Value | Meaning | Flow Field Behavior |
|-------|---------|-------------------|
| `100` | Default passable ground | Normal pathing (cost = 100) |
| `40` | Mud / slow zone (soft_cost) | Entities move slower |
| `300` | Danger zone (hard_cost) | Pathfinder avoids but CAN path through if no alternative |
| `60001–65534` | Destructible wall (hard_cost) | Very high cost — pathfinder strongly avoids |
| `65535` | Permanent impassable wall | Pathfinder treats as BLOCKED — never routes through |

> [!IMPORTANT]
> **Default terrain cost is 100, NOT 0.** The flow field Dijkstra uses costs additively.
> A cost of 0 means "free" (teleportation). A cost of 100 is the standard baseline for open ground.
> When generating flat terrain (no obstacles), fill both `hard_costs` and `soft_costs` with `100`.

### Terrain Payload Format (sent in ZMQ reset)

```json
{
  "hard_costs": [100, 100, 65535, ...],
  "soft_costs": [100, 40, 100, ...],
  "width": 30,
  "height": 30,
  "cell_size": 20.0
}
```
- Array is row-major: `index = y * width + x`
- `cell_size` maps grid coords to world coords: `world_x = grid_x * cell_size`

---

## 6. Pheromone & Repellent (Zone Modifiers)

**File:** `micro-core/src/systems/directive_executor/executor.rs` (SetZoneModifier)

Pheromone and Repellent work by temporarily modifying terrain costs around a world coordinate.

### How It Works

Python sends a `SetZoneModifier` directive:
```json
{
  "directive": "SetZoneModifier",
  "target_faction": 0,
  "x": 200.0, "y": 300.0,
  "radius": 60.0,
  "cost_modifier": -50
}
```

> **Duration:** The ticks_remaining is NOT set per-directive. It comes from
> `BuffConfig.zone_modifier_duration_ticks` which is set during environment
> reset via `AbilityConfigPayload.zone_modifier_duration_ticks`.

- **Negative `cost_modifier`** = Pheromone (attract) — reduces terrain cost, making the flow field prefer this area
- **Positive `cost_modifier`** = Repellent — increases terrain cost, making the flow field avoid this area
- **`ticks_remaining`** — configurable via `zone_modifier_duration_ticks` in `AbilityConfigPayload` (sent in reset). Default: 120 ticks (~2 seconds). Tactical curriculum uses 1500 ticks (~25 seconds / ~10 RL steps).
- Zones modify the flow field on next recalculation

### Flow Field Impact

The flow field pathfinder adds zone modifiers to the base terrain cost:
```
effective_cost = hard_cost + sum(zone_modifiers_at_cell)
```
So a pheromone (cost_modifier = -50) on a 100-cost cell → 50 cost → preferred path.
A repellent (+200) on a 100-cost cell → 300 cost → avoided path.

---

## 7. Movement System

**File:** `micro-core/src/systems/movement.rs`

### Movement Pipeline (per tick)

1. **Flow field lookup** — entity reads the flow vector at its grid cell
2. **Separation force** — Boids-style repulsion from nearby same-faction entities
3. **Speed calculation:**
   ```
   base_speed = movement.max_speed (from profile)
   speed_mult = get_multiplier(faction, entity, movement_speed_stat)
   terrain_mult = soft_cost[cell] / 100.0  (100 = normal, 40 = 0.4x speed)
   final_speed = base_speed * speed_mult * terrain_mult
   ```
4. **Wall sliding** — if next position hits an impassable cell, slide along the wall

### Key Config (tactical_curriculum.json)

```json
"movement": {
  "max_speed": 60.0,
  "steering_factor": 5.0,
  "separation_radius": 6.0,
  "separation_weight": 1.5,
  "flow_weight": 1.0
}
```

---

## 8. Navigation System (Directives → Flow Field)

**File:** `micro-core/src/systems/directive_executor/executor.rs`

### Navigation Targets

| Directive | NavigationTarget | Effect |
|-----------|-----------------|--------|
| `UpdateNavigation` | `Waypoint { x, y }` | Compute flow field from (x,y), faction follows it |
| `UpdateNavigation` | `Faction { faction_id }` | Compute flow field toward that faction's centroid |
| `Hold` | (removes nav rule) | Stop movement, entities idle in place |
| `Retreat` | `Waypoint { x, y }` | Same as UpdateNavigation with waypoint |

The flow field is a Dijkstra-computed vector field: every grid cell stores a direction vector pointing toward the target. Entities follow these vectors automatically each tick.

---

## 9. MacroDirective Vocabulary (Rust-side)

**File:** `micro-core/src/bridges/zmq_protocol/directives.rs`

| Directive | Fields | Python Action |
|-----------|--------|---------------|
| `Idle` | — | Hold (no-op) |
| `UpdateNavigation` | `follower_faction`, `target` | AttackCoord, Scout nav |
| `ActivateBuff` | `faction`, `modifiers[]`, `duration_ticks`, `targets` | Debuff trigger |
| `Retreat` | `faction`, `retreat_x`, `retreat_y` | Retreat action |
| `SetZoneModifier` | `target_faction`, `x`, `y`, `radius`, `cost_modifier` | Pheromone / Repellent |
| `SplitFaction` | `source_faction`, `new_sub_faction`, `percentage`, `epicenter` | SplitToCoord / Scout |
| `MergeFaction` | `source_faction`, `target_faction` | MergeBack |
| `SetAggroMask` | `source_faction`, `target_faction`, `allow_combat` | Used by split mechanics |

---

## 10. Win/Loss Detection (Python-side)

**File:** `macro-brain/src/env/swarm_env.py`

Win/loss is computed in Python from the state snapshot faction counts:

- **WIN:** All enemy factions have 0 entities (brain killed everyone)
- **LOSS:** Brain faction has 0 entities (brain is dead)
- **TIMEOUT:** `step_count >= max_steps` (neither side eliminated)

### Debuff Mechanic (Target Selection Reward)

When the **target faction** is eliminated before the trap faction:
1. Python detects target count dropped to 0
2. `_apply_trap_debuff()` sends `ActivateBuff` to Rust
3. Trap's combat damage is reduced to 25%
4. Trap's bot controller switches from `HoldPosition` to `Charge` (enrages toward brain)
5. Brain fights the weakened, charging trap → should win

> [!WARNING]
> The debuff only reduces **damage output** (stat_index 2). It does NOT reduce trap HP.
> The HP modifier (stat_index 0) in the buff config is a no-op — see Section 3 Caution.

---

## 11. Fog of War

**File:** `micro-core/src/visibility.rs`, `micro-core/src/systems/visibility.rs`

- **Explored grid:** Bit-packed grid tracking which cells have ever been seen (persists)
- **Visible grid:** Which cells are currently in line-of-sight of any faction entity (recomputed each tick)
- **Wall-aware BFS:** Visibility spreads from each entity up to vision range, blocked by impassable terrain
- **ZMQ filtering:** When fog is enabled, the state snapshot only includes entities in visible cells

### Fog Schedule in Curriculum

| Stages 0–3 | Stages 4+ |
|-------------|-----------|
| `fog_enabled: false` | `fog_enabled: true` |
| Full visibility | Partial observation |

---

## 12. Spatial Grid

**File:** `micro-core/src/spatial/`

O(1) neighbor queries using a hash grid. Cell size matches interaction range for optimal performance.

- `grid.query_radius(center, radius)` returns all entities within radius
- Used by: interaction system (combat), separation force (movement), visibility BFS

---

## Quick Reference: Combat Math Template

```
Given:
  brain_count=50, brain_hp=100, brain_dps_per_unit=25
  trap_count=50,  trap_hp=200,  trap_dps_per_unit=25

Without debuff:
  brain_total_hp = 50 * 100 = 5,000
  brain_total_dps = 50 * 25 = 1,250
  trap_total_hp = 50 * 200 = 10,000
  trap_total_dps = 50 * 25 = 1,250

  time_brain_kills_trap = 10,000 / 1,250 = 8.0s
  time_trap_kills_brain = 5,000 / 1,250 = 4.0s
  → Brain DIES at 4.0s (trap has 5,000 HP remaining)

With debuff (trap damage × 0.25):
  trap_total_dps = 50 * 25 * 0.25 = 312.5
  time_brain_kills_trap = 10,000 / 1,250 = 8.0s  (HP unchanged!)
  time_trap_kills_brain = 5,000 / 312.5 = 16.0s
  → Brain WINS at 8.0s (trap is dead, brain has ~2,500 HP remaining)
```
