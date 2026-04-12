# Algorithm Study: Composite Steering — Macro Flow + Micro Boids

**Date:** 2026-04-04 (Original), 2026-04-13 (Boids 2.0 Upgrade)  
**Domain:** Swarm AI, Steering Behaviors, Game Physics  
**Full Specification:** [implementation_plan_task_06.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_06.md)  
**Implementation:** [micro-core/src/systems/movement.rs](../../micro-core/src/systems/movement.rs), [tactical_sensor.rs](../../micro-core/src/systems/tactical_sensor.rs)  
**Tags:** `boids`, `steering`, `flow-field`, `swarm`, `kinematics`, `subsumption`, `tactical`

---

## 1. Problem Statement

10,000 entities must navigate toward goals while avoiding each other. Pure flow
field following creates a "swarm crush" — all entities converge to the same point,
creating infinite density. Pure Boids separation prevents goal-seeking. We need to
**blend** both forces.

## 2. The Three-Force Model (Boids 2.0)

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  MACRO PUSH:   │ +   │  MICRO PUSH:   │ +   │ TACTICAL PUSH: │
│  Flow Field    │     │  Boids Separ.  │     │ Kite/PeelForA  │
│  (global nav)  │     │  (local avoid) │     │ (10 Hz sensor) │
└────────────────┘     └────────────────┘     └────────────────┘
      60 Hz                 60 Hz                 10 Hz
                                                  (entity sharded)
                        ↓ Blended desired_vel
                        → Momentum lerp
                        → Terrain clamp
```

### 2.1 Macro: Flow Field Sampling (O(1))

```rust
let macro_dir = flow_field.sample(entity_pos);  // Normalized Vec2
```

One lookup per entity per tick. The flow field encodes the collective pathfinding
result from the Chamfer Dijkstra (see Study 006).

### 2.2 Micro: Boids Separation (O(K) via Spatial Hash)

```rust
let mut separation_dir = Vec2::ZERO;
grid.for_each_in_radius(current_pos, separation_radius, |n_entity, n_pos| {
    if n_entity == entity { return; }
    let diff = current_pos - n_pos;
    let dist_sq = diff.length_squared();
    if dist_sq > 0.0001 {
        separation_dir += diff / dist_sq;  // Inverse-distance repulsion
    }
});
```

**Repulsion formula:** `force = direction / distance²`
- Close neighbors: strong repulsion (prevents overlap)
- Far neighbors: weak repulsion (doesn't interfere with navigation)
- Exact overlap (`dist_sq < 0.0001`): deterministic spread using entity ID bits

### 2.3 Perfect Overlap Breaker

When two entities are at exactly the same position, `diff = ZERO` and no natural
repulsion exists. We use entity ID bits for a deterministic pseudo-random angle:

```rust
let bits = entity.to_bits();
let angle = (bits % 360) as f32 * TAU / 360.0;
separation_dir += Vec2::new(angle.cos(), angle.sin()) * 0.1;
```

This prevents stable dead-locks without introducing randomness that would break
deterministic simulation.

## 3. Force Blending (Boids 2.0)

```rust
// Engagement range hold: suppress flow when enemy is in range
let effective_flow_weight = if tactical.engagement_range > 0.0 && enemy_in_range {
    0.0  // Hold position at range
} else {
    mc.flow_weight
};

// 3-vector blend
let desired = (macro_dir * effective_flow_weight)
    + (separation_dir * mc.separation_weight)
    + (tactical.direction * tactical.weight);
let desired = desired.normalize_or_zero() * max_speed;
```

| Parameter | Default | Purpose |
|:---|:---|:---|
| `flow_weight` | 1.0 | Strength of global navigation toward goals |
| `separation_weight` | 1.0 | Strength of local collision avoidance |
| `tactical.weight` | 0.0–3.0 | 10 Hz sensor output (behavior-dependent) |
| `max_speed` | 50.0 | Maximum velocity magnitude (world units/sec) |
| `engagement_range` | 0.0 | Distance at which flow is suppressed (0 = melee) |

`normalize_or_zero()` is critical — prevents `NaN` when all forces are zero.

## 4. Momentum Smoothing (Velocity Lerp)

```rust
let new_vel = current_vel.lerp(desired_vel, steering_factor * dt);
```

**Without lerp:** Entities snap to new direction instantly — robotic, unrealistic.
**With lerp:** Smooth turning, momentum persistence, organic movement.

- `steering_factor = 0.5` at `dt = 1/60`: effective lerp rate ≈ 0.83% per tick
- Entities take ~120 ticks (2 seconds) to fully change direction
- Higher steering_factor = more responsive (less momentum)

## 5. Terrain-Aware Wall Sliding

When an entity's next position would enter a wall cell (`hard_cost = u16::MAX`),
the movement system applies **kinematic wall-sliding**:

```rust
if terrain.hard_cost_at_world(next_x, pos.y) == u16::MAX {
    next_x = pos.x;  // Block X component
}
if terrain.hard_cost_at_world(pos.x, next_y) == u16::MAX {
    next_y = pos.y;  // Block Y component
}
```

**Why per-axis blocking?** If the entity moves diagonally into a wall, blocking
BOTH axes creates a "sticky wall" — entity stops dead. Per-axis blocking lets the
entity **slide along the wall** on the unblocked axis, which feels natural.

### Soft Cost Speed Reduction

```rust
let effective_speed = max_speed * (terrain.soft_cost / 100.0);
```

- `soft_cost = 100` → normal speed
- `soft_cost = 50` → half speed (mud/swamp)
- `soft_cost = 0` → frozen (wall with soft permeability 0)

## 6. Boundary Clamping

```rust
pos.x = next_x.clamp(0.0, world_width);
pos.y = next_y.clamp(0.0, world_height);
```

Prevents entities from escaping the world bounds.

## 7. Static Faction Mode

Factions in `FactionBehaviorMode::static_factions` skip flow field sampling
entirely. Their `macro_dir = ZERO` — they only respond to Boids separation.

Use case: Defender faction (faction 1) is stationary. It doesn't pursue; it only
gets attacked.

## 8. Performance: par_iter_mut()

```rust
query.par_iter_mut().for_each(|(entity, mut pos, mut vel, faction, mc)| {
    // Each entity mutates ONLY its own Position and Velocity
    // Safe for parallel execution across CPU cores
});
```

Each entity reads shared resources (`FlowField`, `SpatialHashGrid`, `TerrainGrid`)
and writes only its own components. Bevy's `par_iter_mut()` distributes this across
CPU cores automatically.

## 9. The "Swarm Crush" Without Separation

Without Boids separation, 500 entities following the same flow field converge to
a single point, creating a density singularity:

```
Without separation:        With separation:
    ●●●●●                   ● ● ● ● ●
    ●●●●●                  ●  ●  ●  ●
    ●●●●● → ● (crush)     ●  ●  ●  ●  → natural swarm
    ●●●●●                  ●  ●  ●  ●
    ●●●●●                   ● ● ● ● ●
```

This is why Boids separation is not optional — it's fundamental to visual quality.

## 10. Tactical Sensor (10 Hz, Entity-Sharded)

**File:** `micro-core/src/systems/tactical_sensor.rs`

The tactical sensor evaluates per-class behaviors from the `UnitTypeRegistry` and writes
the subsumption-winning vector to `TacticalState`.

### Entity Sharding

Instead of skipping 5 frames and spiking on the 6th, work is distributed evenly:

```rust
if entity.index_u32() % 6 != (tick.tick % 6) as u32 { continue; }
```

This means each tick evaluates ~N/6 entities. Over 6 ticks, every entity gets
updated exactly once = 10 Hz effective. CPU load stays constant.

### Subsumption (Not Summation)

If multiple behaviors trigger, only the highest-weight wins:

```
Kite(weight=1) says: flee left
PeelForAlly(weight=3) says: rush right

Result: rush right (weight=3 wins)
```

Summation would produce: `left + right = zero` (vector cancellation).
Subsumption produces: the protector rushes to save the ranger.

### Behavior Catalog

| Behavior | Parameters | Direction |
|----------|-----------|----------|
| `Kite` | `trigger_radius`, `weight` | Away from nearest enemy |
| `PeelForAlly` | `target_class`, `search_radius`, `require_recent_damage`, `weight` | Toward distressed ally |

### Damage Detection

`interaction_system` stamps `CombatState.last_damaged_tick` when an entity takes damage.
`PeelForAlly` checks: `tick - last_damaged_tick < 30` (= last 0.5 seconds).

