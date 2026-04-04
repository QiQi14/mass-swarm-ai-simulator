# Task 03: Systems + Config

```yaml
Task_ID: task_03_systems_config
Feature: P1-MP1 Rust/Bevy Scaffold + Minimal ECS
Execution_Phase: B (parallel with Task 02 — zero file overlap)
Model_Tier: standard
```

## Target Files
- `micro-core/src/systems/mod.rs` [MODIFY]
- `micro-core/src/systems/movement.rs` [NEW]
- `micro-core/src/systems/spawning.rs` [NEW]
- `micro-core/src/config.rs` [NEW]
- `micro-core/src/lib.rs` [MODIFY] (add `pub mod config;`)

## Dependencies
- **Task 01** must be complete (project must compile)
- **Reads contract from Task 02** (component types) — but does NOT modify Task 02's files. Import paths are known from the shared contract in `implementation_plan.md`.

## Context_Bindings
- context/conventions
- context/architecture
- skills/rust-code-standards

## Strict Instructions

### 1. Create `src/config.rs`

```rust
use bevy::prelude::*;
use serde::{Deserialize, Serialize};

/// Global simulation configuration. Inserted as a Bevy Resource at app startup.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub world_width: f32,
    pub world_height: f32,
    pub initial_entity_count: u32,
}

impl Default for SimulationConfig {
    fn default() -> Self {
        Self {
            world_width: 1000.0,
            world_height: 1000.0,
            initial_entity_count: 100,
        }
    }
}

/// Monotonically increasing tick counter. Incremented once per ECS tick.
#[derive(Resource, Debug, Default)]
pub struct TickCounter {
    pub tick: u64,
}
```

### 2. Update `src/lib.rs`

Add the config module. The file should now be:

```rust
pub mod components;
pub mod config;
pub mod systems;
```

### 3. Create `src/systems/movement.rs`

```rust
use bevy::prelude::*;
use crate::components::{Position, Velocity};
use crate::config::SimulationConfig;

/// Applies velocity to position each tick, with world-boundary wrapping.
///
/// Entities that exit the [0, world_width] × [0, world_height] bounds
/// wrap around to the opposite edge. This prevents entities from
/// drifting off into infinity in the pre-pathfinding phase.
pub fn movement_system(
    mut query: Query<(&mut Position, &Velocity)>,
    config: Res<SimulationConfig>,
) {
    for (mut pos, vel) in &mut query {
        pos.x += vel.dx;
        pos.y += vel.dy;

        // Wrap around world boundaries
        if pos.x < 0.0 {
            pos.x += config.world_width;
        } else if pos.x >= config.world_width {
            pos.x -= config.world_width;
        }

        if pos.y < 0.0 {
            pos.y += config.world_height;
        } else if pos.y >= config.world_height {
            pos.y -= config.world_height;
        }
    }
}
```

### 4. Create `src/systems/spawning.rs`

```rust
use bevy::prelude::*;
use rand::Rng;
use crate::components::{EntityId, NextEntityId, Position, Team, Velocity};
use crate::config::SimulationConfig;

/// Startup system: spawns `initial_entity_count` entities with random
/// positions, small random velocities, and alternating teams.
///
/// Uses a seeded RNG for deterministic, reproducible results.
pub fn initial_spawn_system(
    mut commands: Commands,
    config: Res<SimulationConfig>,
    mut next_id: ResMut<NextEntityId>,
) {
    let mut rng = rand::rng();

    for i in 0..config.initial_entity_count {
        let team = if i % 2 == 0 { Team::Swarm } else { Team::Defender };

        let entity_id = EntityId { id: next_id.0 };
        next_id.0 += 1;

        commands.spawn((
            entity_id,
            Position {
                x: rng.random_range(0.0..config.world_width),
                y: rng.random_range(0.0..config.world_height),
            },
            Velocity {
                dx: rng.random_range(-1.0..1.0),
                dy: rng.random_range(-1.0..1.0),
            },
            team,
        ));
    }
}
```

> **Note on RNG:** Using `rand::rng()` which creates a thread-local RNG. For reproducibility, we could use `StdRng::seed_from_u64(42)` later. For now, we use the default RNG for simplicity.

### 5. Create `tick_counter_system` (in `systems/mod.rs` or a separate file)

Add the tick counter system. Place it in `systems/mod.rs` since it's trivial:

### 6. Update `src/systems/mod.rs`

```rust
pub mod movement;
pub mod spawning;

use bevy::prelude::*;
use crate::config::TickCounter;

pub use movement::movement_system;
pub use spawning::initial_spawn_system;

/// Increments the global tick counter each frame.
pub fn tick_counter_system(mut counter: ResMut<TickCounter>) {
    counter.tick += 1;
}
```

### 7. Write Unit Tests

**movement.rs tests:**

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;

    #[test]
    fn test_movement_applies_velocity() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig::default());
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 100.0, y: 200.0 },
            Velocity { dx: 1.5, dy: -0.5 },
        )).id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        assert!((pos.x - 101.5).abs() < f32::EPSILON);
        assert!((pos.y - 199.5).abs() < f32::EPSILON);
    }

    #[test]
    fn test_movement_wraps_at_right_boundary() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig {
            world_width: 100.0,
            world_height: 100.0,
            initial_entity_count: 0,
        });
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 99.5, y: 50.0 },
            Velocity { dx: 1.0, dy: 0.0 },
        )).id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        assert!(pos.x < 1.0, "Entity should have wrapped to near 0, got {}", pos.x);
    }

    #[test]
    fn test_movement_wraps_at_left_boundary() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig {
            world_width: 100.0,
            world_height: 100.0,
            initial_entity_count: 0,
        });
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 0.5, y: 50.0 },
            Velocity { dx: -1.0, dy: 0.0 },
        )).id();

        app.update();

        let pos = app.world().get::<Position>(entity).unwrap();
        assert!(pos.x > 99.0, "Entity should have wrapped to near 100, got {}", pos.x);
    }
}
```

**config.rs tests:**

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = SimulationConfig::default();
        assert!((config.world_width - 1000.0).abs() < f32::EPSILON);
        assert!((config.world_height - 1000.0).abs() < f32::EPSILON);
        assert_eq!(config.initial_entity_count, 100);
    }

    #[test]
    fn test_tick_counter_default() {
        let counter = TickCounter::default();
        assert_eq!(counter.tick, 0);
    }
}
```

## Verification_Strategy

```yaml
Test_Type: unit
Test_Stack: cargo (Rust toolchain)
Acceptance_Criteria:
  - "`cargo build` succeeds"
  - "`cargo clippy` — zero warnings"
  - "movement_system correctly applies velocity to position"
  - "boundary wrapping works for left, right, top, and bottom edges"
  - "initial_spawn_system creates exactly `initial_entity_count` entities"
  - "All spawned entities have unique EntityId values"
  - "SimulationConfig::default() returns 1000x1000 world, 100 entities"
  - "TickCounter::default() starts at 0"
  - "`cargo test` — all unit tests pass"
Suggested_Test_Commands:
  - "cd micro-core && cargo test systems 2>&1"
  - "cd micro-core && cargo test config 2>&1"
  - "cd micro-core && cargo clippy 2>&1"
```
