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

use crate::components::{
    EntityId, FactionId, MovementConfig, NextEntityId, Position, StatBlock, UnitClassId, Velocity,
    VisionRadius,
};
use crate::config::SimulationConfig;
use bevy::prelude::*;
use rand::Rng;

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
        let faction = FactionId(i % config.initial_faction_count);

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
            StatBlock::with_defaults(&config.initial_stat_defaults),
            VisionRadius::default(),
            MovementConfig::default(),
            UnitClassId::default(),
            crate::components::TacticalState::default(),
            crate::components::CombatState::default(),
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
        let count = app
            .world_mut()
            .query::<&EntityId>()
            .iter(app.world())
            .count();
        assert_eq!(count, 5, "Should have spawned exactly 5 entities");

        // Assert uniqueness
        let ids: Vec<_> = app
            .world_mut()
            .query::<&EntityId>()
            .iter(app.world())
            .map(|e| e.id)
            .collect();
        let mut sorted_ids = ids.clone();
        sorted_ids.sort();
        sorted_ids.dedup();
        assert_eq!(
            ids.len(),
            sorted_ids.len(),
            "Each spawned entity should have unique EntityId"
        );
    }

    #[test]
    fn test_initial_spawn_configurable_factions() {
        // Arrange
        let mut app = App::new();
        let mut config = SimulationConfig::default();
        config.world_width = 100.0;
        config.world_height = 100.0;
        config.initial_entity_count = 9;
        config.initial_faction_count = 3; // 3 factions instead of default 2
        app.insert_resource(config);
        app.insert_resource(NextEntityId(1));
        app.add_systems(Startup, initial_spawn_system);

        // Act
        app.update();

        // Assert — check that faction IDs 0, 1, 2 all appear
        let factions: Vec<u32> = app
            .world_mut()
            .query::<&FactionId>()
            .iter(app.world())
            .map(|f| f.0)
            .collect();
        assert!(factions.contains(&0), "Should have faction 0");
        assert!(factions.contains(&1), "Should have faction 1");
        assert!(factions.contains(&2), "Should have faction 2");
        assert_eq!(
            factions.iter().filter(|&&f| f == 0).count(),
            3,
            "3 entities per faction"
        );
    }
}
