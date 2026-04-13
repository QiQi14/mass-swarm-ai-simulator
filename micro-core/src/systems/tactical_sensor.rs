//! # Tactical Sensor System
//!
//! 10 Hz sharded sensor loop that evaluates tactical behaviors from the
//! `UnitTypeRegistry` and writes subsumption-winning vectors to `TacticalState`.
//!
//! ## Architecture
//! - Runs every tick but processes only 1/6th of entities per frame
//!   (entity sharding: `entity.index_u32() % 6 == tick % 6`)
//! - Uses `SpatialHashGrid` with embedded faction_id for zero-ECS-lookup
//!   proximity queries
//! - Subsumption: highest-weight behavior wins exclusively (no vector cancellation)
//!
//! ## Ownership
//! - **Task:** T06 — Tactical Sensor System (Boids 2.0)
//! - **Contract:** implementation_plan.md → T06
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, TacticalState, CombatState}`
//! - `crate::components::unit_class::UnitClassId`
//! - `crate::config::{TickCounter, UnitTypeRegistry}`
//! - `crate::config::unit_registry::TacticalBehavior`
//! - `crate::spatial::SpatialHashGrid`

use bevy::prelude::*;

use crate::components::{FactionId, Position, TacticalState, CombatState};
use crate::components::unit_class::UnitClassId;
use crate::config::{TickCounter, UnitTypeRegistry};
use crate::config::unit_registry::TacticalBehavior;
use crate::spatial::SpatialHashGrid;

/// Number of recent ticks to consider as "recently damaged" for PeelForAlly.
/// At 60 TPS, 30 ticks = 0.5 seconds.
const RECENT_DAMAGE_THRESHOLD: u64 = 30;

/// Evaluates tactical behaviors for 1/6th of entities each tick (10 Hz effective).
///
/// For each entity in this frame's shard:
/// 1. Look up its unit class in the `UnitTypeRegistry`
/// 2. Evaluate each tactical behavior (Kite, PeelForAlly)
/// 3. Write the subsumption winner (highest weight) to `TacticalState`
///
/// Entities with no tactical behaviors or no registry entry get TacticalState::default()
/// (zero vector, zero weight = pure flow follower).
///
/// ## Performance
/// - Each tick processes ~N/6 entities (entity sharding eliminates CPU spikes)
/// - Grid queries use embedded faction_id (zero ECS lookups for faction checks)
/// - O(N/6 × B × K) per tick where B = behaviors per class, K = neighbors in range
pub fn tactical_sensor_system(
    tick: Res<TickCounter>,
    registry: Res<UnitTypeRegistry>,
    grid: Res<SpatialHashGrid>,
    mut q_entities: Query<(
        Entity,
        &Position,
        &FactionId,
        &UnitClassId,
        &mut TacticalState,
    )>,
    q_combat: Query<&CombatState>,
    q_class: Query<&UnitClassId>,
) {
    // Early exit if no unit types defined
    if registry.types.is_empty() {
        return;
    }

    let shard = (tick.tick % 6) as u32;

    for (entity, pos, faction, class_id, mut tactical) in q_entities.iter_mut() {
        // Entity sharding: only process 1/6th of entities per tick
        if entity.index_u32() % 6 != shard {
            continue;
        }

        // Look up behaviors for this entity's class
        let unit_def = match registry.get(class_id.0) {
            Some(def) if !def.behaviors.is_empty() => def,
            _ => {
                // No tactical behaviors — reset to neutral
                tactical.direction = Vec2::ZERO;
                tactical.weight = 0.0;
                continue;
            }
        };

        let my_pos = Vec2::new(pos.x, pos.y);
        let my_faction = faction.0;

        // Subsumption: evaluate all behaviors, highest weight wins
        let mut best_dir = Vec2::ZERO;
        let mut best_weight: f32 = 0.0;

        for behavior in &unit_def.behaviors {
            match behavior {
                TacticalBehavior::Kite { trigger_radius, weight } => {
                    // Find nearest enemy within trigger_radius
                    let mut nearest_enemy_pos: Option<Vec2> = None;
                    let mut nearest_dist_sq = f32::MAX;

                    grid.for_each_in_radius(my_pos, *trigger_radius, |_e, e_pos, e_faction| {
                        if e_faction != my_faction {
                            let dist_sq = (e_pos - my_pos).length_squared();
                            if dist_sq < nearest_dist_sq {
                                nearest_dist_sq = dist_sq;
                                nearest_enemy_pos = Some(e_pos);
                            }
                        }
                    });

                    if let Some(enemy_pos) = nearest_enemy_pos {
                        let flee_dir = (my_pos - enemy_pos).normalize_or_zero();
                        if *weight > best_weight && flee_dir != Vec2::ZERO {
                            best_dir = flee_dir;
                            best_weight = *weight;
                        }
                    }
                }

                TacticalBehavior::PeelForAlly {
                    target_class,
                    search_radius,
                    require_recent_damage,
                    weight,
                } => {
                    // Find nearest distressed ally of target_class
                    let mut nearest_ally_pos: Option<Vec2> = None;
                    let mut nearest_dist_sq = f32::MAX;

                    grid.for_each_in_radius(my_pos, *search_radius, |ally_entity, ally_pos, ally_faction| {
                        // Must be same faction
                        if ally_faction != my_faction {
                            return;
                        }
                        // Must be the target class
                        if let Ok(ally_class) = q_class.get(ally_entity) {
                            if ally_class.0 != *target_class {
                                return;
                            }
                        } else {
                            return;
                        }
                        // Optionally check if recently damaged
                        if *require_recent_damage {
                            if let Ok(combat) = q_combat.get(ally_entity) {
                                if combat.last_damaged_tick == 0
                                    || tick.tick.saturating_sub(combat.last_damaged_tick) > RECENT_DAMAGE_THRESHOLD
                                {
                                    return; // Not recently damaged
                                }
                            } else {
                                return; // No CombatState = can't verify
                            }
                        }
                        let dist_sq = (ally_pos - my_pos).length_squared();
                        if dist_sq < nearest_dist_sq && dist_sq > 0.0 {
                            nearest_dist_sq = dist_sq;
                            nearest_ally_pos = Some(ally_pos);
                        }
                    });

                    if let Some(ally_pos) = nearest_ally_pos {
                        let rush_dir = (ally_pos - my_pos).normalize_or_zero();
                        if *weight > best_weight && rush_dir != Vec2::ZERO {
                            best_dir = rush_dir;
                            best_weight = *weight;
                        }
                    }
                }
            }
        }

        // Write subsumption winner
        tactical.direction = best_dir;
        tactical.weight = best_weight;
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::components::{EntityId, FactionId, Position};
    use crate::config::unit_registry::UnitTypeDef;

    fn setup_app() -> App {
        let mut app = App::new();
        app.insert_resource(SpatialHashGrid::new(20.0));
        app.init_resource::<TickCounter>();
        app.init_resource::<UnitTypeRegistry>();
        app.add_systems(Update, tactical_sensor_system);
        app
    }

    #[test]
    fn test_kite_flees_from_enemy() {
        // Arrange
        let mut app = setup_app();
        let mut registry = UnitTypeRegistry::default();
        registry.types.insert(1, UnitTypeDef {
            engagement_range: 100.0,
            movement: None,
            behaviors: vec![TacticalBehavior::Kite {
                trigger_radius: 50.0,
                weight: 2.0,
            }],
        });
        app.insert_resource(registry);

        // Ranger (class 1) at (100, 100)
        let ranger = app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 100.0, y: 100.0 },
            FactionId(0),
            UnitClassId(1),
            TacticalState::default(),
            CombatState::default(),
        )).id();

        // Enemy at (120, 100) — within trigger_radius (50)
        let enemy = app.world_mut().spawn((
            EntityId { id: 2 },
            Position { x: 120.0, y: 100.0 },
            FactionId(1),
            UnitClassId(0),
            TacticalState::default(),
            CombatState::default(),
        )).id();

        // Set tick so ranger is in shard 0
        // entity.index_u32() % 6 must equal tick % 6
        let ranger_shard = ranger.index_u32() % 6;
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (ranger, Vec2::new(100.0, 100.0), 0),
                (enemy, Vec2::new(120.0, 100.0), 1),
            ]);
            let mut tick_res = app.world_mut().resource_mut::<TickCounter>();
            tick_res.tick = ranger_shard as u64;
        }

        // Act
        app.update();

        // Assert
        let ts = app.world().get::<TacticalState>(ranger).unwrap();
        assert!(ts.weight > 0.0, "Kite weight should be positive, got {}", ts.weight);
        // Flee direction should be roughly (-1, 0) — away from enemy
        assert!(ts.direction.x < 0.0, "Should flee left (away from enemy at +X), got {:?}", ts.direction);
    }

    #[test]
    fn test_no_behaviors_stays_neutral() {
        // Arrange
        let mut app = setup_app();
        // Registry has class 0 with no behaviors
        let mut registry = UnitTypeRegistry::default();
        registry.types.insert(0, UnitTypeDef {
            engagement_range: 0.0,
            movement: None,
            behaviors: vec![],
        });
        app.insert_resource(registry);

        let entity = app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 50.0, y: 50.0 },
            FactionId(0),
            UnitClassId(0),
            TacticalState { direction: Vec2::X, weight: 5.0, engagement_range: 0.0 },
            CombatState::default(),
        )).id();

        let shard = entity.index_u32() % 6;
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(entity, Vec2::new(50.0, 50.0), 0)]);
            let mut tick_res = app.world_mut().resource_mut::<TickCounter>();
            tick_res.tick = shard as u64;
        }

        // Act
        app.update();

        // Assert — should be reset to neutral
        let ts = app.world().get::<TacticalState>(entity).unwrap();
        assert_eq!(ts.direction, Vec2::ZERO, "No-behavior entity should have zero direction");
        assert!((ts.weight - 0.0).abs() < f32::EPSILON, "No-behavior entity should have zero weight");
    }

    #[test]
    fn test_subsumption_highest_weight_wins() {
        // Arrange: entity with Kite(weight=1) and PeelForAlly(weight=3)
        // If ally is distressed AND enemy is near, PeelForAlly should win
        let mut app = setup_app();
        let mut registry = UnitTypeRegistry::default();
        registry.types.insert(2, UnitTypeDef {
            engagement_range: 0.0,
            movement: None,
            behaviors: vec![
                TacticalBehavior::Kite {
                    trigger_radius: 100.0,
                    weight: 1.0,
                },
                TacticalBehavior::PeelForAlly {
                    target_class: 1,
                    search_radius: 100.0,
                    require_recent_damage: true,
                    weight: 3.0,
                },
            ],
        });
        app.insert_resource(registry);

        // Protector (class 2) at origin
        let protector = app.world_mut().spawn((
            EntityId { id: 1 },
            Position { x: 0.0, y: 0.0 },
            FactionId(0),
            UnitClassId(2),
            TacticalState::default(),
            CombatState::default(),
        )).id();

        // Distressed ally (class 1) at (50, 0) — same faction, recently damaged
        let _ally = app.world_mut().spawn((
            EntityId { id: 2 },
            Position { x: 50.0, y: 0.0 },
            FactionId(0),
            UnitClassId(1),
            TacticalState::default(),
            CombatState { last_damaged_tick: 5 },
        )).id();

        // Enemy at (-30, 0) — within kite range
        let _enemy = app.world_mut().spawn((
            EntityId { id: 3 },
            Position { x: -30.0, y: 0.0 },
            FactionId(1),
            UnitClassId(0),
            TacticalState::default(),
            CombatState::default(),
        )).id();

        let shard = protector.index_u32() % 6;
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (protector, Vec2::new(0.0, 0.0), 0),
                (_ally, Vec2::new(50.0, 0.0), 0),
                (_enemy, Vec2::new(-30.0, 0.0), 1),
            ]);
            let mut tick_res = app.world_mut().resource_mut::<TickCounter>();
            tick_res.tick = shard as u64 + 6; // Use shard + 6 so tick >= ally damage tick
        }

        // Act
        app.update();

        // Assert — PeelForAlly (weight=3) should win over Kite (weight=1)
        let ts = app.world().get::<TacticalState>(protector).unwrap();
        assert!((ts.weight - 3.0).abs() < f32::EPSILON,
            "PeelForAlly weight (3.0) should win, got {}", ts.weight);
        // Direction should be toward ally (+X)
        assert!(ts.direction.x > 0.0,
            "Should rush toward ally at +X, got {:?}", ts.direction);
    }
}
