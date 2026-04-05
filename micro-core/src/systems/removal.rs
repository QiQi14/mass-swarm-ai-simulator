//! # Removal System
//!
//! Config-driven entity removal based on stat thresholds.
//! Uses Commands for deferred despawn — no borrow conflicts.
//!
//! ## Ownership
//! - **Task:** task_05_interaction_removal_systems
//! - **Contract:** implementation_plan.md → Contracts 5, 6, 7
//!
//! ## Depends On
//! - `crate::components::{EntityId, StatBlock}`
//! - `crate::rules::{RemovalRuleSet, RemovalCondition, RemovalEvents}`

use bevy::prelude::*;
use crate::components::{EntityId, StatBlock};
use crate::rules::{RemovalRuleSet, RemovalCondition, RemovalEvents};

/// Checks all entities against removal rules and despawns those
/// crossing stat thresholds.
///
/// Uses `Commands` for deferred despawn — entity is removed at end of frame.
/// No iterator invalidation, no borrow conflicts.
/// Records removed entity IDs in `RemovalEvents` for WebSocket broadcast.
///
/// ## Note on Negative Stats
/// Stats are NOT clamped. Health at -150.0 provides "Overkill Gradient"
/// signal to the Python Macro-Brain for learning efficient unit allocation.
pub fn removal_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    rules: Res<RemovalRuleSet>,
    query: Query<(Entity, &EntityId, &StatBlock)>,
    mut commands: Commands,
    mut events: ResMut<RemovalEvents>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    // Clear previous tick's removal events
    events.removed_ids.clear();

    for (entity, entity_id, stat_block) in query.iter() {
        for rule in &rules.rules {
            // Bounds check stat index
            if rule.stat_index >= stat_block.0.len() {
                continue;
            }

            let stat_value = stat_block.0[rule.stat_index];

            let should_remove = match rule.condition {
                RemovalCondition::LessOrEqual => stat_value <= rule.threshold,
                RemovalCondition::GreaterOrEqual => stat_value >= rule.threshold,
            };

            if should_remove {
                events.removed_ids.push(entity_id.id);
                commands.entity(entity).despawn();
                break; // Don't process more rules for this entity
            }
        }
    }
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.removal_us = s.elapsed().as_micros() as u32;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rules::RemovalRule;

    fn setup_app() -> App {
        let mut app = App::new();
        app.insert_resource(RemovalRuleSet { rules: vec![] });
        app.insert_resource(RemovalEvents::default());
        app.add_systems(Update, removal_system);
        app
    }

    #[test]
    fn test_entity_dies_less_or_equal() {
        let mut app = setup_app();

        app.insert_resource(RemovalRuleSet {
            rules: vec![
                RemovalRule {
                    stat_index: 0,
                    threshold: 0.0,
                    condition: RemovalCondition::LessOrEqual,
                },
            ],
        });

        let entity = app.world_mut().spawn((
            EntityId { id: 42 },
            StatBlock::with_defaults(&[(0, 0.0)]),
        )).id(); // Dies

        app.update();

        assert!(app.world().get_entity(entity).is_err()); // Despawned

        let events = app.world().resource::<RemovalEvents>();
        assert_eq!(events.removed_ids, vec![42]);
    }

    #[test]
    fn test_entity_alive_less_or_equal() {
        let mut app = setup_app();

        app.insert_resource(RemovalRuleSet {
            rules: vec![
                RemovalRule {
                    stat_index: 0,
                    threshold: 0.0,
                    condition: RemovalCondition::LessOrEqual,
                },
            ],
        });

        let entity = app.world_mut().spawn((
            EntityId { id: 99 },
            StatBlock::with_defaults(&[(0, 50.0)]),
        )).id(); // Lives

        app.update();

        assert!(app.world().get_entity(entity).is_ok()); // Stays alive

        let events = app.world().resource::<RemovalEvents>();
        assert!(events.removed_ids.is_empty());
    }

    #[test]
    fn test_entity_dies_greater_or_equal() {
        let mut app = setup_app();

        app.insert_resource(RemovalRuleSet {
            rules: vec![
                RemovalRule {
                    stat_index: 0,
                    threshold: 100.0,
                    condition: RemovalCondition::GreaterOrEqual,
                },
            ],
        });

        let entity = app.world_mut().spawn((
            EntityId { id: 100 },
            StatBlock::with_defaults(&[(0, 100.0)]),
        )).id(); // Crosses upper threshold

        app.update();

        assert!(app.world().get_entity(entity).is_err()); // Despawned

        let events = app.world().resource::<RemovalEvents>();
        assert_eq!(events.removed_ids, vec![100]);
    }

    #[test]
    fn test_entity_alive_greater_or_equal() {
        let mut app = setup_app();

        app.insert_resource(RemovalRuleSet {
            rules: vec![
                RemovalRule {
                    stat_index: 0,
                    threshold: 100.0,
                    condition: RemovalCondition::GreaterOrEqual,
                },
            ],
        });

        let entity = app.world_mut().spawn((
            EntityId { id: 101 },
            StatBlock::with_defaults(&[(0, 99.0)]),
        )).id(); // Does not cross threshold

        app.update();

        assert!(app.world().get_entity(entity).is_ok()); // Stays alive

        let events = app.world().resource::<RemovalEvents>();
        assert!(events.removed_ids.is_empty());
    }
}
