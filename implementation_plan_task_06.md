# Task 06 — FlowFieldFollower + Movement + Spawning (Full Specification)

> **Parent Plan:** [`implementation_plan.md`](./implementation_plan.md) → Contracts 4, 5, 7, 9, 10
> **Architecture:** Composite Steering (Macro Flow + Micro Boids) with Zero-Allocation closure-based spatial queries
> **This file:** Exhaustive spec for the Executor agent.

**Phase:** 2 (Parallel) | **Tier:** `standard` | **Domain:** ECS Systems + Components  
**Target Files:**
- `components/movement_config.rs` [NEW]
- `components/mod.rs` [MODIFY]
- `config.rs` [MODIFY]
- `systems/movement.rs` [MODIFY]
- `systems/flow_field_update.rs` [NEW]
- `systems/spawning.rs` [MODIFY]

**Dependencies:** Task 02 (SpatialHashGrid), Task 03 (FlowFieldRegistry), Task 04 (Rule Resources)  
**Context Bindings:** `context/conventions`, `context/architecture`, `skills/rust-code-standards`

> **DO NOT** modify `systems/mod.rs` — Task 08 handles wiring.

---

## 1. The Physics Problem: Infinite Density Singularity

A Flow Field calculates the optimal path but ignores entity mass. Without physical volume, 5,000 entities following a gradient toward a single Defender will compress into the **exact same X/Y coordinate**.

### Solution: Composite Steering (Macro + Micro)

Blend a **Macro-Goal** (Flow Field gradient) with a **Micro-Force** (Boids Separation):

```
desired_velocity = (flow_direction × flow_weight) + (separation_push × separation_weight)
velocity = lerp(current_velocity, desired_velocity, steering_factor × dt)
```

### Zero-Sqrt Separation Math

Standard Boids separation requires `sqrt()` for distance. At 30K neighbor checks/tick, this is a CPU bottleneck.

**Shortcut:** Let $\vec{D} = \text{self\_pos} - \text{neighbor\_pos}$. Divide by squared length:

$$\frac{\vec{D}}{|\vec{D}|^2} = \frac{\hat{D}}{|\vec{D}|}$$

Result magnitude: $\frac{1}{|\vec{D}|}$ — **inverse-linear repulsion**. Pushes hard when close, softly when far. Zero `sqrt()` calls.

> [!WARNING]
> The user's code comment said "Inverse-Square push" but the math produces **inverse-linear** (`1/d`, not `1/d²`). The spec corrects the comment. The formula itself is correct and desirable.

---

## 2. The Memory Allocation Trap: Patching Task 02

### The Problem

`SpatialHashGrid::query_radius()` returns `Vec<(Entity, Vec2)>`. Calling this for 10,000 entities every tick = **600,000 heap allocations/second**.

### The Fix: Zero-Allocation Closure Method

Add `for_each_in_radius` to `SpatialHashGrid` — **this patches Task 02's hash_grid.rs**.

> [!IMPORTANT]
> Task 02's `Target_Files` must be updated to include this method. Since Task 02 is PENDING, we add the method spec to the Task 02 brief directly. The executor building Task 02 will implement both `query_radius()` (for Task 05 interaction) and `for_each_in_radius()` (for Task 06 movement).

```rust
impl SpatialHashGrid {
    /// Zero-allocation radius query. Executes closure `f` for each entity found.
    ///
    /// Unlike `query_radius()`, this allocates nothing — the closure processes
    /// each entity in-place. Used by the movement system for 10K+ entity
    /// separation queries at 60 TPS.
    pub fn for_each_in_radius<F>(&self, center: Vec2, radius: f32, mut f: F)
    where
        F: FnMut(Entity, Vec2),
    {
        let radius_sq = radius * radius;
        let min_cell = self.world_to_cell(center - Vec2::splat(radius));
        let max_cell = self.world_to_cell(center + Vec2::splat(radius));

        for cy in min_cell.y..=max_cell.y {
            for cx in min_cell.x..=max_cell.x {
                if let Some(bucket) = self.grid.get(&IVec2::new(cx, cy)) {
                    for &(entity, pos) in bucket {
                        let diff = pos - center;
                        if diff.length_squared() <= radius_sq {
                            f(entity, pos);
                        }
                    }
                }
            }
        }
    }
}
```

---

## 3. Multithreading: The Paradigm Flip

In Task 05 (interaction), `par_iter()` was FORBIDDEN — multiple entities mutate the same Defender's stats.

**In Task 06, the paradigm reverses.** Movement is **self-contained**: each entity mutates only its OWN `Position` and `Velocity`. Reading from `SpatialHashGrid` and `FlowFieldRegistry` is purely immutable.

**Zero aliased mutability → safe to use `par_iter_mut()`.**

This distributes 10,000 entity updates across all CPU cores automatically.

---

## 4. Critical Design Decisions (MANDATORY)

1. **Composite Steering** — Flow field + Boids separation. NOT raw flow field alone.
2. **Zero-Sqrt separation** — `diff / dist_sq` (inverse-linear). NO `sqrt()`.
3. **`par_iter_mut()`** — Multi-threaded. Each entity mutates only its own data.
4. **`for_each_in_radius` closure** — Zero-allocation spatial queries. NOT `query_radius()`.
5. **Position clamping** — `clamp(0, world_width)`. NOT toroidal wrapping.
6. **Fixed delta `1.0/60.0`** — ML determinism. NOT `Res<Time>`.
7. **Flow field update at ~2 TPS** — `tick % interval == 0`. NOT every tick.
8. **Keep existing `Velocity { dx, dy }`** — Do NOT change to `Velocity(Vec2)`. Breaks WS serialization.

---

## 5. Full Rust Implementation

### 5.1 `micro-core/src/components/movement_config.rs` [NEW]

```rust
//! # Movement Configuration Component
//!
//! Per-entity movement tuning: speed, steering, separation.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7

use bevy::prelude::*;

/// Per-entity movement configuration. Entities with this component
/// participate in flow-field navigation and Boids separation.
/// Entities WITHOUT this component retain Phase 1 behavior (random drift).
#[derive(Component, Debug, Clone, Copy)]
pub struct MovementConfig {
    /// Maximum speed in world units per second.
    pub max_speed: f32,
    /// Lerp factor for velocity steering (higher = snappier turns).
    pub steering_factor: f32,
    /// Personal space bubble radius for Boids separation (world units).
    pub separation_radius: f32,
    /// Strength multiplier for separation push-back.
    pub separation_weight: f32,
    /// Strength multiplier for flow field pull.
    pub flow_weight: f32,
}

impl Default for MovementConfig {
    fn default() -> Self {
        Self {
            max_speed: 60.0,
            steering_factor: 5.0,
            separation_radius: 6.0,
            separation_weight: 1.5,
            flow_weight: 1.0,
        }
    }
}
```

### 5.2 `micro-core/src/components/mod.rs` [MODIFY]

Add:
```rust
pub mod movement_config;
pub use movement_config::MovementConfig;
```

### 5.3 `micro-core/src/config.rs` [MODIFY]

Add new fields to `SimulationConfig`:

```rust
pub struct SimulationConfig {
    // ... existing fields ...

    /// Ticks between flow field recalculations (default: 30 = ~2 updates/sec).
    pub flow_field_update_interval: u64,

    /// Ticks between wave spawns (default: 120 = every 2 seconds).
    pub wave_spawn_interval: u64,

    /// Number of entities per spawn wave.
    pub wave_spawn_count: u32,

    /// Faction ID for spawned wave entities.
    pub wave_spawn_faction: u32,

    /// Default stat values for spawned wave entities.
    /// Format: Vec of (stat_index, value) pairs.
    pub wave_spawn_stat_defaults: Vec<(usize, f32)>,
}
```

Update `Default`:
```rust
flow_field_update_interval: 30,
wave_spawn_interval: 120,
wave_spawn_count: 10,
wave_spawn_faction: 0,
wave_spawn_stat_defaults: vec![(0, 1.0)],
```

### 5.4 `micro-core/src/systems/movement.rs` [MODIFY — FULL REWRITE]

```rust
//! # Movement System (Phase 2)
//!
//! Composite Steering: Macro Flow Field + Micro Boids Separation.
//! Multi-threaded via par_iter_mut() — each entity mutates only its own data.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7
//!
//! ## Depends On
//! - `crate::components::{Position, Velocity, FactionId, MovementConfig}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::pathfinding::FlowFieldRegistry`
//! - `crate::rules::{NavigationRuleSet, FactionBehaviorMode}`
//! - `crate::config::SimulationConfig`

use bevy::prelude::*;
use bevy::utils::HashMap;
use crate::components::{Position, Velocity, FactionId, MovementConfig};
use crate::spatial::SpatialHashGrid;
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::{NavigationRuleSet, FactionBehaviorMode};
use crate::config::SimulationConfig;

/// Multi-threaded movement with Composite Steering.
///
/// ## Algorithm per entity
/// 1. **Macro Pull** — Sample flow field for entity's faction → direction vector.
/// 2. **Micro Push** — Query SpatialHashGrid for separation neighbors → push-back.
/// 3. **Blend & Steer** — Weighted sum → lerp velocity for organic momentum.
/// 4. **Kinematics** — Apply velocity × dt. Clamp to world boundaries.
///
/// ## Threading
/// Safe to `par_iter_mut()` because each entity mutates ONLY its own
/// `Position` and `Velocity`. Grid/Registry reads are purely immutable.
///
/// ## Entities WITHOUT MovementConfig
/// Entities without `MovementConfig` are NOT processed by this system.
/// They retain Phase 1 behavior (random drift) via the simple movement
/// system in the legacy path. The integration task (T08) should handle
/// which movement system runs for which entities.
pub fn movement_system(
    grid: Res<SpatialHashGrid>,
    registry: Res<FlowFieldRegistry>,
    nav_rules: Res<NavigationRuleSet>,
    behavior_mode: Res<FactionBehaviorMode>,
    config: Res<SimulationConfig>,
    mut query: Query<(Entity, &mut Position, &mut Velocity, &FactionId, &MovementConfig)>,
) {
    let dt = 1.0 / 60.0;

    // Cache follower→target mapping (small allocation, rules count is tiny)
    let follow_map: HashMap<u32, u32> = nav_rules.rules.iter()
        .map(|r| (r.follower_faction, r.target_faction))
        .collect();

    // PARALLEL ITERATOR: distribute across CPU cores
    query.par_iter_mut().for_each(|(entity, mut pos, mut vel, faction, mc)| {
        let current_pos = Vec2::new(pos.x, pos.y);

        // --- 1. MACRO PULL: Flow Field ---
        let mut macro_dir = Vec2::ZERO;

        // Only sample flow field if faction is NOT in static mode
        if !behavior_mode.static_factions.contains(&faction.0) {
            if let Some(&target_faction) = follow_map.get(&faction.0) {
                if let Some(field) = registry.fields.get(&target_faction) {
                    macro_dir = field.sample(current_pos);
                }
            }
        }

        // --- 2. MICRO PUSH: Boids Separation (Zero-Allocation) ---
        let mut separation_dir = Vec2::ZERO;

        grid.for_each_in_radius(current_pos, mc.separation_radius, |n_ent, n_pos| {
            if n_ent != entity {
                let diff = current_pos - n_pos;
                let dist_sq = diff.length_squared();

                if dist_sq > 0.0001 {
                    // Inverse-linear repulsion: diff / |diff|² = direction / distance
                    // Pushes hard when close, softly when far. Zero sqrt().
                    separation_dir += diff / dist_sq;
                } else {
                    // Break perfect overlaps with deterministic spread
                    // Use entity index bits for pseudo-random direction
                    let bits = entity.index();
                    let angle = (bits % 360) as f32 * std::f32::consts::TAU / 360.0;
                    separation_dir += Vec2::new(angle.cos(), angle.sin()) * 0.1;
                }
            }
        });

        // --- 3. BLEND & STEER ---
        let desired = (macro_dir * mc.flow_weight)
                    + (separation_dir * mc.separation_weight);
        let desired = desired.normalize_or_zero() * mc.max_speed;

        // Lerp velocity for organic momentum (entities curve, not snap)
        let new_vel = Vec2::new(vel.dx, vel.dy).lerp(desired, mc.steering_factor * dt);

        vel.dx = new_vel.x;
        vel.dy = new_vel.y;

        // --- 4. KINEMATICS & CLAMPING ---
        pos.x = (pos.x + vel.dx * dt).clamp(0.0, config.world_width);
        pos.y = (pos.y + vel.dy * dt).clamp(0.0, config.world_height);
    });
}
```

> [!WARNING]
> **Velocity struct:** The existing `Velocity { dx, dy }` struct uses separate f32 fields (not `Velocity(Vec2)`). This is required for WS serialization compatibility. The movement system must convert: `Vec2::new(vel.dx, vel.dy)` for math, then write back `vel.dx = ...; vel.dy = ...;`.

### 5.5 `micro-core/src/systems/flow_field_update.rs` [NEW]

```rust
//! # Flow Field Update System
//!
//! Recalculates flow fields at ~2 TPS (every N ticks).
//! Decoupled from the 60 TPS physics loop.
//!
//! ## Ownership
//! - **Task:** task_06_flow_field_movement_spawning
//! - **Contract:** implementation_plan.md → Contract 7

use bevy::prelude::*;
use bevy::utils::HashMap;
use crate::components::{Position, FactionId};
use crate::config::{SimulationConfig, TickCounter};
use crate::pathfinding::FlowFieldRegistry;
use crate::rules::NavigationRuleSet;

/// Recalculates flow fields for navigating factions.
/// Runs every `config.flow_field_update_interval` ticks (~2 TPS at interval=30).
pub fn flow_field_update_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    nav_rules: Res<NavigationRuleSet>,
    query: Query<(&Position, &FactionId)>,
    mut registry: ResMut<FlowFieldRegistry>,
) {
    // Skip tick 0 and only run at configured interval
    if tick.tick == 0 || tick.tick % config.flow_field_update_interval != 0 {
        return;
    }

    // Deduplicate target factions from nav rules
    let target_factions: Vec<u32> = {
        let mut targets: Vec<u32> = nav_rules.rules.iter()
            .map(|r| r.target_faction)
            .collect();
        targets.sort_unstable();
        targets.dedup();
        targets
    };

    // Gather goal positions per target faction (O(N) pass)
    let mut faction_goals: HashMap<u32, Vec<Vec2>> = HashMap::default();
    for (pos, faction) in query.iter() {
        if target_factions.contains(&faction.0) {
            faction_goals.entry(faction.0)
                .or_default()
                .push(Vec2::new(pos.x, pos.y));
        }
    }

    // Calculate flow fields using Task 03 algorithm
    let grid_w = (config.world_width / 20.0).ceil() as usize;  // cell_size from Task 02
    let grid_h = (config.world_height / 20.0).ceil() as usize;

    for &target in &target_factions {
        if let Some(goals) = faction_goals.get(&target) {
            if goals.is_empty() { continue; }

            let mut field = crate::pathfinding::FlowField::new(grid_w, grid_h, 20.0);
            field.calculate(goals, &[]); // No obstacles in Phase 2
            registry.fields.insert(target, field);
        }
    }

    // Clean up fields for factions no longer targeted
    registry.fields.retain(|k, _| target_factions.contains(k));
}
```

### 5.6 `micro-core/src/systems/spawning.rs` [MODIFY]

Add `wave_spawn_system` function. Keep existing `initial_spawn_system`.

```rust
/// Periodic wave spawner. Spawns entities at world edges every N ticks.
pub fn wave_spawn_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
) {
    // Skip tick 0 and only run at configured interval
    if tick.tick == 0 || tick.tick % config.wave_spawn_interval != 0 {
        return;
    }

    let spread = 20.0; // Deterministic spread to prevent pixel-stacking

    for i in 0..config.wave_spawn_count {
        let id = next_id.0;
        next_id.0 += 1;

        // Spawn along top edge with deterministic spread
        let offset_x = (i as f32 % 10.0) * spread;
        let offset_y = (i as f32 / 10.0).floor() * spread;

        commands.spawn((
            EntityId { id },
            Position { x: 50.0 + offset_x, y: 10.0 + offset_y },
            Velocity { dx: 0.0, dy: 0.0 },
            FactionId(config.wave_spawn_faction),
            StatBlock::with_defaults(&config.wave_spawn_stat_defaults),
            MovementConfig::default(),
        ));
    }
}
```

Also update `initial_spawn_system` to add `MovementConfig::default()` to faction 0 entities:
```rust
// Inside the spawn loop, add MovementConfig for faction 0:
let mut entity_cmd = commands.spawn(( ... ));
if faction.0 == config.wave_spawn_faction {
    entity_cmd.insert(MovementConfig::default());
}
```

---

## 6. The Bevy DAG (System Execution Order — Task 08 Reference)

```rust
app.add_systems(
    FixedUpdate,
    (
        wave_spawn_system,            // 1. Matter is created
        update_spatial_grid_system,   // 2. Space is cataloged
        flow_field_update_system,     // 3. Brain updates pathing (~2 TPS)
        interaction_system,           // 4. Damage applied (Zero-Alloc Disjoint)
        removal_system,               // 5. Dead matter removed
        movement_system,              // 6. Surviving matter steers (Multi-threaded)
    ).chain()
);
```

---

## 7. Corrections from Human-Provided Code

| # | User's Code | Issue | Correction |
|---|-------------|-------|------------|
| 1 | `Velocity(pub Vec2)` | Existing: `Velocity { dx, dy }` — WS serialization breaks | Keep `{ dx, dy }`, convert inside system |
| 2 | Comment: "Inverse-Square push" | Math: `diff/dist_sq` = `1/d` = **inverse-linear** | Corrected comment |
| 3 | `map_width = 1000.0` hardcoded | `SimulationConfig.world_width` exists | Use `config.world_width` |
| 4 | `tick.0` | TickCounter has named field: `tick.tick` | Use `tick.tick` |
| 5 | `Vec2::new(0.1, 0.1)` for overlap break | Deterministic = all entities get same nudge | Use `entity.index()` bits for pseudo-random angle |
| 6 | FlowFieldFollower marker removed | User replaced with MovementConfig | Accepted — MovementConfig subsumes marker role |

---

## 8. Edge Cases

| Edge Case | Behavior | How Handled |
|-----------|----------|-------------|
| No flow field for faction | `macro_dir = Vec2::ZERO` | Separation-only movement |
| Static faction | No flow field lookup | `behavior_mode.static_factions.contains()` guard |
| Entity without MovementConfig | Not processed | Query filter excludes |
| Perfect position overlap | Deterministic spread | `entity.index()` bits → angle |
| Entity at world edge | Clamps to boundary | `.clamp(0.0, world_width)` |
| No neighbors in separation radius | `separation_dir = Vec2::ZERO` | Flow-only movement |
| Empty nav rules | `follow_map` empty | No flow field lookup |
| Tick 0 | No spawn or field update | `tick.tick == 0` → return |

---

## 9. Unit Tests

### Movement Tests:
- **Entity with MovementConfig follows flow field:** Entity at (0,0), flow field pointing right → velocity gains positive dx.
- **Static faction ignores flow field:** Faction in `static_factions` → `macro_dir` stays ZERO.
- **Separation pushes entities apart:** Two entities at same position → velocities diverge after one tick.
- **Boundary clamping:** Entity at (999, 500) with positive dx → x stays ≤ world_width.
- **Entity without MovementConfig excluded:** Entity with only Position/Velocity → not affected by new system.

### Flow Field Update Tests:
- **Runs at interval:** System skips ticks where `tick % interval != 0`.
- **Deduplicates target factions:** Two rules targeting faction 1 → only one field calculated.
- **Cleans up stale fields:** Remove rule → field removed from registry.

### Spawning Tests:
- **Wave spawn count:** After `wave_spawn_interval` ticks, exactly `wave_spawn_count` entities spawned.
- **Spawned entities have MovementConfig:** New entities include the component.
- **Skip tick 0:** No spawn on initialization.

---

## 10. Verification Strategy

```yaml
Verification_Strategy:
  Test_Type: unit
  Test_Stack: cargo test
  Acceptance_Criteria:
    - "MovementConfig entities navigate toward flow field targets"
    - "Separation prevents entity stacking"
    - "Static factions use random drift"
    - "Position clamps to world boundaries"
    - "par_iter_mut used for multi-threaded update"
    - "for_each_in_radius used (NOT query_radius) in movement"
    - "Flow field updates at config interval, not every tick"
    - "Wave spawn creates correct count at correct interval"
  Suggested_Test_Commands:
    - "cd micro-core && cargo test movement"
    - "cd micro-core && cargo test spawning"
    - "cd micro-core && cargo test flow_field_update"
```
