//! # Spawning System
//!
//! Spawns entities at initialization.
//!
//! ## Ownership
//! - **Task:** task_03_systems_config
//! - **Contract:** implementation_plan.md → Shared Contracts → System Signatures
//!
//! ## Depends On
//! - `crate::components::{EntityId, FactionId, NextEntityId, Position, StatBlock, Velocity}`
//! - `crate::config::SimulationConfig`

use bevy::prelude::*;
use rand::Rng;
use crate::components::{EntityId, FactionId, NextEntityId, Position, StatBlock, Velocity, MovementConfig, VisionRadius};
use crate::config::{SimulationConfig, TickCounter};

/// Startup system: spawns `initial_entity_count` entities with random
/// positions, small random velocities, and alternating factions.
///
/// Uses standard ThreadRng for non-deterministic testing.
///
/// # Arguments
/// * `commands` - Bevy command buffer to spawn entities
/// * `config` - Used for spawn bounds and count
/// * `next_id` - Monotonically increasing ID assigning resource
pub fn initial_spawn_system(
    mut commands: Commands,
    config: Res<SimulationConfig>,
    mut next_id: ResMut<NextEntityId>,
) {
    let mut rng = rand::rng();

    for i in 0..config.initial_entity_count {
        let faction = FactionId(if i % 2 == 0 { 0 } else { 1 });

        let entity_id = EntityId { id: next_id.0 };
        // Tick up ID counter for sequential identifiers
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
            faction,
            StatBlock::with_defaults(&[(0, 1.0)]),
            VisionRadius::default(),
            MovementConfig::default(),
        ));
    }
}

/// Periodic wave spawner. Spawns entities at world edges every N ticks.
pub fn wave_spawn_system(
    tick: Res<TickCounter>,
    config: Res<SimulationConfig>,
    mut commands: Commands,
    mut next_id: ResMut<NextEntityId>,
) {
    // Skip tick 0 and only run at configured interval
    if tick.tick == 0 || !tick.tick.is_multiple_of(config.wave_spawn_interval) {
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
            VisionRadius::default(),
        ));
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;

    #[test]
    fn test_initial_spawn_creates_correct_entity_count() {
        // Arrange
        let mut app = App::new();
        let mut config = SimulationConfig::default();
        config.world_width = 100.0;
        config.world_height = 100.0;
        config.initial_entity_count = 5;
        app.insert_resource(config);
        app.insert_resource(NextEntityId(1));
        app.add_systems(Startup, initial_spawn_system);

        // Act
        app.update(); // Runs startup systems

        // Assert
        let count = app.world_mut().query::<&EntityId>().iter(app.world()).count();
        assert_eq!(count, 5, "Should have spawned exactly 5 entities");
        
        // Assert uniqueness
        let ids: Vec<_> = app.world_mut().query::<&EntityId>()
                              .iter(app.world())
                              .map(|e| e.id)
                              .collect();
        let mut sorted_ids = ids.clone();
        sorted_ids.sort();
        sorted_ids.dedup();
        assert_eq!(ids.len(), sorted_ids.len(), "Each spawned entity should have unique EntityId");
    }

    #[test]
    fn test_wave_spawn_creates_correct_count() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(TickCounter { tick: 300 }); // config default interval
        app.insert_resource(NextEntityId(1));
        app.add_systems(Update, wave_spawn_system);

        app.update();

        let count = app.world_mut().query::<&MovementConfig>().iter(app.world()).count();
        assert_eq!(count, 50, "Should have spawned 50 flow field followers");
    }

    #[test]
    fn test_wave_spawn_skips_tick_0() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(TickCounter { tick: 0 });
        app.insert_resource(NextEntityId(1));
        app.add_systems(Update, wave_spawn_system);

        app.update();

        let count = app.world_mut().query::<&MovementConfig>().iter(app.world()).count();
        assert_eq!(count, 0, "Should skip tick 0");
    }
}
