# Navigation & Movement

## 7. Movement System (Boids 2.0 — 3-Vector Blending)

**File:** `micro-core/src/systems/movement.rs`

### Movement Pipeline (per tick, 60 Hz)

```
V_desired = (V_flow × W_flow) + (V_sep × W_sep) + (V_tactical × W_tactical)
```

1. **V_flow: Flow field lookup** — entity reads the flow vector at its grid cell (macro navigation)
2. **V_sep: Boids separation** — inverse-distance repulsion from nearby entities via spatial grid
3. **V_tactical: Tactical steering** — subsumption winner from the 10 Hz tactical sensor (Kite, PeelForAlly)
4. **W_flow dynamic suppression** — engagement range hold: if entity has `engagement_range > 0` and an enemy is within that range, `W_flow → 0` (ranged units hold position)
5. **Speed calculation:**
   ```
   base_speed = movement.max_speed (from profile)
   speed_mult = get_multiplier(faction, entity, movement_speed_stat)
   terrain_mult = soft_cost[cell] / 100.0  (100 = normal, 40 = 0.4x speed)
   final_speed = base_speed * speed_mult * terrain_mult
   ```
6. **Wall sliding** — if next position hits an impassable cell, slide along the wall
7. **Boundary clamping** — entities cannot escape world bounds

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

### Movement Override Resolution (3-tier)

When spawning entities, movement config is resolved in priority order:
1. **Per-spawn override** (`spawn.movement` in ResetEnvironment)
2. **Per-class override** (`UnitTypeDefinition.movement` from UnitTypeRegistry)
3. **Global override** (`reset.movement_config` in ResetEnvironment)
4. **Default** (`MovementConfig::default()`)

---

## 7a. Tactical Sensor System (10 Hz)

**File:** `micro-core/src/systems/tactical_sensor.rs`

Evaluates unit-class-specific tactical behaviors and writes subsumption-winning vectors to `TacticalState`.

### Entity Sharding (No CPU Spikes)

Instead of processing all entities every 6th frame (which causes a CPU spike), the sensor distributes work evenly:
```
if entity.index_u32() % 6 != (tick % 6) as u32 { continue; }
```
Each tick processes exactly 1/6th of all entities → 10 Hz effective update rate.

### Subsumption Architecture

Multiple behaviors are evaluated per entity, but only the **highest-weight wins exclusively**:
```
for behavior in unit_def.behaviors {
    if behavior.weight > best_weight && has_valid_target {
        best_dir = computed_direction;
        best_weight = behavior.weight;
    }
}
```

This prevents vector cancellation — if Kite says "flee left" and PeelForAlly says "rush right", the higher-weight behavior wins completely.

### Behavior Types

| Behavior | Trigger | Direction | Use Case |
|----------|---------|-----------|----------|
| `Kite` | Enemy within `trigger_radius` | Flee (away from nearest enemy) | Rangers staying at range |
| `PeelForAlly` | Ally of `target_class` recently damaged | Rush (toward distressed ally) | Protectors saving rangers |

### Damage Stamping

`CombatState.last_damaged_tick` is stamped by `interaction_system` whenever an entity takes damage. This enables `PeelForAlly` to detect distressed allies within a configurable `RECENT_DAMAGE_THRESHOLD` (default: 30 ticks = 0.5s).

---

## 7b. Unit Type Registry

**File:** `micro-core/src/config/unit_registry.rs`

A Bevy ECS resource mapping `class_id → UnitTypeDef`. Populated from `ResetEnvironment.unit_types`, rebuilt each episode.

```json
"unit_types": [
  {
    "class_id": 1,
    "engagement_range": 150.0,
    "stats": [{ "index": 0, "value": 80.0 }],
    "movement": { "max_speed": 50.0, "flow_weight": 0.8, ... },
    "tactical_behaviors": [
      { "Kite": { "trigger_radius": 50.0, "weight": 2.0 } }
    ]
  }
]
```

### ECS Components (Boids 2.0)

| Component | File | Purpose |
|-----------|------|---------|
| `TacticalState` | `components/tactical.rs` | 10 Hz sensor output: direction, weight, engagement_range |
| `CombatState` | `components/tactical.rs` | Tracks `last_damaged_tick` for ally protection |
| `UnitClassId` | `components/unit_class.rs` | Maps entity to class in UnitTypeRegistry |

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

## 12. Spatial Grid

**File:** `micro-core/src/spatial/`

O(1) neighbor queries using a hash grid. Cell size matches interaction range for optimal performance.

- Grid payload: `(Entity, Vec2, u32)` — embeds `faction_id` to avoid ECS random-access lookups
- `grid.for_each_in_radius(center, radius, |entity, pos, faction| { ... })` — zero-allocation closure
- Used by: interaction (combat), separation (movement), tactical sensor (10 Hz), visibility BFS

---