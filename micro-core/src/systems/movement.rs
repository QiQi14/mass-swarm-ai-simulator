//! # Movement System
//!
//! Applies velocity to position each tick with world-boundary wrapping.
//!
//! ## Ownership
//! - **Task:** task_03_systems_config
//! - **Contract:** implementation_plan.md → Shared Contracts → System Signatures
//!
//! ## Depends On
//! - `crate::components::{Position, Velocity}`
//! - `crate::config::SimulationConfig`

use bevy::prelude::*;
use crate::components::{Position, Velocity};
use crate::config::{SimulationConfig, SimSpeed};

/// Applies velocity to position each tick, with world-boundary wrapping.
///
/// Entities that exit the `[0, world_width]` × `[0, world_height]` bounds
/// wrap around to the opposite edge. This prevents entities from
/// drifting off into infinity in the pre-pathfinding phase.
///
/// # Arguments
/// * `query` - Contains the `Position` (mutable) and `Velocity` of each entity
/// * `config` - Extracted boundary dimensions
pub fn movement_system(
    mut query: Query<(&mut Position, &Velocity)>,
    config: Res<SimulationConfig>,
    speed: Res<SimSpeed>,
) {
    for (mut pos, vel) in &mut query {
        pos.x += vel.dx * speed.multiplier;
        pos.y += vel.dy * speed.multiplier;

        // Wrap around world boundaries (toroidal topology)
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

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use bevy::app::App;

    #[test]
    fn test_movement_applies_velocity() {
        // Arrange
        let mut app = App::new();
        app.insert_resource(SimulationConfig::default());
        app.insert_resource(SimSpeed::default());
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 100.0, y: 200.0 },
            Velocity { dx: 1.5, dy: -0.5 },
        )).id();

        // Act
        app.update();

        // Assert
        let pos = app.world().get::<Position>(entity).unwrap();
        assert!((pos.x - 101.5).abs() < f32::EPSILON, "x should be 101.5, got {}", pos.x);
        assert!((pos.y - 199.5).abs() < f32::EPSILON, "y should be 199.5, got {}", pos.y);
    }

    #[test]
    fn test_movement_wraps_at_right_boundary() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig {
            world_width: 100.0,
            world_height: 100.0,
            initial_entity_count: 0,
        });
        app.insert_resource(SimSpeed::default());
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 99.5, y: 50.0 },
            Velocity { dx: 1.0, dy: 0.0 },
        )).id();

        // Act
        app.update();

        // Assert
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
        app.insert_resource(SimSpeed::default());
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 0.5, y: 50.0 },
            Velocity { dx: -1.0, dy: 0.0 },
        )).id();

        // Act
        app.update();

        // Assert
        let pos = app.world().get::<Position>(entity).unwrap();
        assert!(pos.x > 99.0, "Entity should have wrapped to near 100, got {}", pos.x);
    }
    
    #[test]
    fn test_movement_wraps_at_bottom_boundary() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig {
            world_width: 100.0,
            world_height: 100.0,
            initial_entity_count: 0,
        });
        app.insert_resource(SimSpeed::default());
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 50.0, y: 99.5 },
            Velocity { dx: 0.0, dy: 1.0 },
        )).id();

        // Act
        app.update();

        // Assert
        let pos = app.world().get::<Position>(entity).unwrap();
        assert!(pos.y < 1.0, "Entity should have wrapped to near 0, got {}", pos.y);
    }
    
    #[test]
    fn test_movement_wraps_at_top_boundary() {
        let mut app = App::new();
        app.insert_resource(SimulationConfig {
            world_width: 100.0,
            world_height: 100.0,
            initial_entity_count: 0,
        });
        app.insert_resource(SimSpeed::default());
        app.add_systems(Update, movement_system);

        let entity = app.world_mut().spawn((
            Position { x: 50.0, y: 0.5 },
            Velocity { dx: 0.0, dy: -1.0 },
        )).id();

        // Act
        app.update();

        // Assert
        let pos = app.world().get::<Position>(entity).unwrap();
        assert!(pos.y > 99.0, "Entity should have wrapped to near 100, got {}", pos.y);
    }
}
