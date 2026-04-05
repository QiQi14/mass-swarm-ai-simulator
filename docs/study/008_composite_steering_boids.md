# Algorithm Study: Composite Steering — Macro Flow + Micro Boids

**Date:** 2026-04-04  
**Domain:** Swarm AI, Steering Behaviors, Game Physics  
**Full Specification:** [implementation_plan_task_06.md](../../.agents/history/20260404_234812_phase_2_universal_core_algorithms/implementation_plan_task_06.md)  
**Implementation:** [micro-core/src/systems/movement.rs](../../micro-core/src/systems/movement.rs)  
**Tags:** `boids`, `steering`, `flow-field`, `swarm`, `kinematics`

---

## 1. Problem Statement

10,000 entities must navigate toward goals while avoiding each other. Pure flow
field following creates a "swarm crush" — all entities converge to the same point,
creating infinite density. Pure Boids separation prevents goal-seeking. We need to
**blend** both forces.

## 2. The Two-Force Model

```
┌────────────────┐     ┌────────────────┐
│  MACRO PUSH:   │ +   │  MICRO PUSH:   │  →  Blended desired_vel
│  Flow Field    │     │  Boids Separ.  │     → Momentum lerp
│  (global nav)  │     │  (local avoid) │     → Terrain clamp
└────────────────┘     └────────────────┘
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

## 3. Force Blending

```rust
let desired = (macro_dir * flow_weight) + (separation_dir * separation_weight);
let desired = desired.normalize_or_zero() * max_speed;
```

| Parameter | Default | Purpose |
|:---|:---|:---|
| `flow_weight` | 1.0 | Strength of global navigation toward goals |
| `separation_weight` | 1.0 | Strength of local collision avoidance |
| `max_speed` | 50.0 | Maximum velocity magnitude (world units/sec) |

`normalize_or_zero()` is critical — prevents `NaN` when both forces are zero.

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
