//! # Engine Override System
//!
//! Applies direct velocity overrides from Tier 1 interventions.
//!
//! ## Ownership
//! - **Task:** task_05_directive_executor_system
//! - **Contract:** implementation_plan_feature_1.md

use bevy::prelude::*;
use crate::components::{Velocity, EngineOverride};
use crate::config::InterventionTracker;

pub fn engine_override_system(
    mut commands: Commands,
    mut query: Query<(Entity, &mut Velocity, &mut EngineOverride)>,
    mut tracker: ResMut<InterventionTracker>,
) {
    tracker.active = !query.is_empty();
    for (entity, mut vel, mut over) in query.iter_mut() {
        vel.dx = over.forced_velocity.x;
        vel.dy = over.forced_velocity.y;
        if let Some(ref mut ticks) = over.ticks_remaining {
            *ticks = ticks.saturating_sub(1);
            if *ticks == 0 {
                commands.entity(entity).remove::<EngineOverride>();
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_engine_override_forces_velocity() {
        let mut app = App::new();
        app.insert_resource(InterventionTracker::default());
        app.add_systems(Update, engine_override_system);

        let entity = app.world_mut().spawn((
            Velocity { dx: 0.0, dy: 0.0 },
            EngineOverride { forced_velocity: Vec2::new(10.0, 20.0), ticks_remaining: None },
        )).id();

        app.update();

        let vel = app.world().get::<Velocity>(entity).unwrap();
        assert_eq!(vel.dx, 10.0);
        assert_eq!(vel.dy, 20.0);
    }

    #[test]
    fn test_engine_override_countdown_and_removal() {
        let mut app = App::new();
        app.insert_resource(InterventionTracker::default());
        app.add_systems(Update, engine_override_system);

        let entity = app.world_mut().spawn((
            Velocity { dx: 0.0, dy: 0.0 },
            EngineOverride { forced_velocity: Vec2::new(5.0, 5.0), ticks_remaining: Some(1) },
        )).id();

        app.update();

        assert!(app.world().get::<EngineOverride>(entity).is_none(), "Should be removed after ticks_remaining goes to 0");
    }
}
