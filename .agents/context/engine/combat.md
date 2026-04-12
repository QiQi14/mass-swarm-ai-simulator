# Entity Model & Combat

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

### Tactical Components (Boids 2.0)

Entities also carry tactical state for the 10 Hz steering sensor:
- **`TacticalState`** — sensor output: `direction` (Vec2), `weight` (f32), `engagement_range` (f32)
- **`CombatState`** — damage tracking: `last_damaged_tick` (u64), stamped by `interaction_system` on every damage event

These enable emergent micro-behaviors (kiting, ally protection) without per-entity pathfinding. See `navigation.md` §7a for details.

**Key files:** `micro-core/src/components/`, `micro-core/src/components/tactical.rs`

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

### Three Damage Delivery Modes

The engine uses **three separate systems** for damage delivery, routed by rule config:

| Rule Config | System | Behavior |
|------------|--------|----------|
| `aoe: None, penetration: None` | `interaction_system` | 1v1 pairwise (nearest target only) |
| `aoe: Some, penetration: None` | `aoe_interaction_system` | Splash zone + gradient falloff |
| `penetration: Some` (±aoe) | `penetration_interaction_system` | Ray + energy absorption |

> [!IMPORTANT]
> **1v1 Constraint:** The standard `interaction_system` enforces strict 1v1 pairwise damage — each source entity damages ONLY the single nearest valid target per rule per tick. Mass concentration works because MANY sources target the same enemy, not one source hitting many.

### Area-of-Effect (AoE) Damage

**File:** `micro-core/src/systems/aoe_interaction.rs`

Enabled by adding `aoe` config to an InteractionRule:
```json
{
  "aoe": {
    "shape": { "type": "Circle", "radius": 20.0 },
    "falloff": "Linear"
  }
}
```

**Shapes:** Circle, Ellipse (semi_major/semi_minor), ConvexPolygon (≤6 vertices, CCW winding)  
**Falloff:** None (uniform), Linear (1−d), Quadratic (1−d²)  
**Rotation:** TargetAligned (default) or Fixed(angle)

Algorithm: find nearest target → impact center → query splash zone → apply `damage × falloff(d_norm)` to all targets inside shape.

### Penetration (Piercing Damage)

**File:** `micro-core/src/systems/penetration.rs`

Enabled by adding `penetration` config to an InteractionRule:
```json
{
  "penetration": {
    "ray_width": 2.0,
    "energy_model": { "Kinetic": { "base_energy": 100.0 } },
    "absorption_stat_index": 0,
    "absorption_ignores_mitigation": true
  }
}
```

**Energy Models:**
- `Kinetic` — burst damage, normalized energy [0,1], absorbed per target hit. Tanks body-block.
- `Beam` — sustained drain, no absorption, all targets along the ray take damage.

Algorithm: find nearest target → cast ray → filter by perpendicular distance (2D cross-product) → sort by distance along ray → sequential energy delivery with absorption.

### AoE + Penetration Composability

Both configs on the same rule enables composite weapons (e.g., cone-shaped shotgun):
- AoE shape provides the **spatial filter** (which targets can be hit)
- Penetration provides the **energy model** (sequential absorption along ray)
- AoE falloff still applies within the shape

Example: Cone shotgun (triangle polygon + kinetic penetration)

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