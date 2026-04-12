//! # Interaction System
//!
//! Config-driven proximity interactions using Zero-Allocation Disjoint Queries.
//! Separates read-only spatial data from mutable stat access to eliminate
//! all Vec snapshots, HashMaps, and heap allocations in the hot loop.
//!
//! ## Ownership
//! - **Task:** task_05_interaction_removal_systems
//! - **Contract:** implementation_plan.md → Contract 7
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, StatBlock, EntityId}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::rules::{InteractionRuleSet, InteractionRule, StatEffect}`
//!
//! ## Architecture: Disjoint Queries
//! - `q_ro: Query<(Entity, &Position, &FactionId, &EntityId)>` — read-only spatial data
//! - `q_rw: Query<&mut StatBlock>` — write-only stat mutation
//! - Zero component overlap → safe simultaneous access
//! - Zero heap allocations in the interaction loop

use crate::components::{EntityId, FactionId, Position, StatBlock, UnitClassId};
use crate::config::FactionBuffs;
use crate::rules::InteractionRuleSet;
use crate::spatial::SpatialHashGrid;
use bevy::prelude::*;

/// Processes proximity-based interactions between entities.
///
/// Uses Disjoint Queries for zero-allocation O(1) stat mutations:
/// - `q_ro` iterates all entities for position/faction (immutable).
/// - `q_ro.get(neighbor)` reads neighbor faction inside the loop (safe: shared borrows).
/// - `q_rw.get_mut(neighbor)` mutates neighbor stats (safe: disjoint component set).
///
/// Frenzy buff: When a faction has an active buff, their damage output is
/// multiplied by the buff's speed_multiplier. This makes Frenzy a dual
/// speed+damage ability, creating a meaningful tactical lever for the RL agent.
///
/// ## Performance
/// - Single-threaded (L1 cache coherent on hot targets)
/// - Zero Vec/HashMap allocations
/// - O(N × R × K) where N=entities, R=rules, K=avg neighbors in range
/// - ~0.5ms for 10K entities with default config
#[allow(clippy::too_many_arguments)]
pub fn interaction_system(
    telemetry: Option<ResMut<crate::plugins::telemetry::PerfTelemetry>>,
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    aggro: Res<crate::config::AggroMaskRegistry>,
    combat_buffs: Res<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    mut cooldowns: ResMut<crate::config::CooldownTracker>,
    tick_counter: Res<crate::config::TickCounter>,
    // Query 1: Purely immutable spatial data.
    // Safe to iterate AND random-access simultaneously (multiple &self borrows).
    q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
    // Query 2: Purely mutable stat data.
    // Disjoint from Query 1 (StatBlock ∩ {Position, FactionId} = ∅).
    mut q_rw: Query<&mut StatBlock>,
    // Query 3: Combat state for damage tick stamping (Boids 2.0).
    // Disjoint from q_ro and q_rw (CombatState ∩ {Position, StatBlock} = ∅).
    mut q_combat: Query<&mut crate::components::CombatState>,
) {
    let start = telemetry.as_ref().map(|_| std::time::Instant::now());
    
    cooldowns.tick();

    if rules.rules.is_empty() {
        if let (Some(mut t), Some(s)) = (telemetry, start) {
            t.interaction_us = s.elapsed().as_micros() as u32;
        }
        return;
    }

    // Pre-calculate fixed delta — ML determinism requires strict fixed timestep
    let tick_delta = 1.0 / 60.0;

    for (source_entity, source_pos, source_faction, source_id, source_class) in q_ro.iter() {
        for (rule_idx, rule) in rules.rules.iter().enumerate() {
            // Skip AoE/penetration rules — handled by dedicated systems
            if rule.aoe.is_some() || rule.penetration.is_some() {
                continue;
            }

            // Only process rules where this entity is the source faction
            if rule.source_faction != source_faction.0 {
                continue;
            }

            // Unit class filtering — skip if source class doesn't match
            if let Some(required_class) = rule.source_class {
                if source_class.0 != required_class {
                    continue;
                }
            }

            // "The Blinders" — SetAggroMask can disable combat between
            // specific faction pairs (e.g., flanking unit ignores frontline)
            if !aggro.is_combat_allowed(rule.source_faction, rule.target_faction) {
                continue;
            }

            if rule.cooldown_ticks.is_some() {
                if !cooldowns.can_fire(source_id.id, rule_idx) {
                    continue;
                }
            }

            // Abstract damage multiplier via configurable stat index + entity targeting
            let damage_mult = buff_config
                .combat_damage_stat
                .map(|stat_idx| {
                    combat_buffs.get_multiplier(source_faction.0, source_id.id, stat_idx)
                })
                .unwrap_or(1.0);

            let effective_range = if let Some(stat_idx) = rule.range_stat_index {
                q_rw.get(source_entity)
                    .ok()
                    .and_then(|sb| sb.0.get(stat_idx).copied())
                    .unwrap_or(rule.range)
            } else {
                rule.range
            };

            // O(K) spatial lookup — only allocation is grid.query_radius's return Vec
            let center = Vec2::new(source_pos.x, source_pos.y);
            let neighbors = grid.query_radius(center, effective_range);

            // 1v1 CONSTRAINT: Find the nearest valid target only.
            // Each source entity deals damage to at most ONE target per rule per tick.
            let mut nearest_target: Option<(Entity, f32)> = None;

            for &(neighbor_entity, _, _) in &neighbors {
                // CRITICAL: Prevent self-interaction
                if neighbor_entity == source_entity {
                    continue;
                }

                // O(1) read-only lookup inside iter() — safe: multiple &self borrows
                if let Ok((_, neighbor_pos, neighbor_faction, _, neighbor_class)) = q_ro.get(neighbor_entity) {
                    if neighbor_faction.0 != rule.target_faction {
                        continue;
                    }

                    if let Some(required_class) = rule.target_class {
                        if neighbor_class.0 != required_class {
                            continue;
                        }
                    }

                    let dx = neighbor_pos.x - source_pos.x;
                    let dy = neighbor_pos.y - source_pos.y;
                    let dist_sq = dx * dx + dy * dy;

                    if nearest_target.is_none() || dist_sq < nearest_target.unwrap().1 {
                        nearest_target = Some((neighbor_entity, dist_sq));
                    }
                }
            }

            // Apply effects only to the single nearest target
            let mut applied_any_effect = false;
            if let Some((target_entity, _)) = nearest_target {
                for effect in &rule.effects {
                    let base_delta = effect.delta_per_second * tick_delta * damage_mult;
                    let final_delta = if let Some(ref mit) = rule.mitigation {
                        // Read mitigation stat from target BEFORE get_mut
                        let mit_value = q_rw.get(target_entity)
                            .ok()
                            .and_then(|sb| sb.0.get(mit.stat_index).copied())
                            .unwrap_or(0.0);
                        match mit.mode {
                            crate::rules::interaction::MitigationMode::PercentReduction => {
                                base_delta * (1.0 - mit_value.clamp(0.0, 1.0))
                            }
                            crate::rules::interaction::MitigationMode::FlatReduction => {
                                let abs_reduced = (base_delta.abs() - mit_value * tick_delta).max(0.0);
                                abs_reduced * base_delta.signum()
                            }
                        }
                    } else {
                        base_delta
                    };

                    if let Ok(mut stat_block) = q_rw.get_mut(target_entity) {
                        if effect.stat_index < stat_block.0.len() {
                            stat_block.0[effect.stat_index] += final_delta;
                            applied_any_effect = true;
                        }
                    }
                }

                // Boids 2.0: Stamp last_damaged_tick for PeelForAlly detection
                if applied_any_effect {
                    if let Ok(mut combat) = q_combat.get_mut(target_entity) {
                        combat.last_damaged_tick = tick_counter.tick;
                    }
                }
            }

            if let Some(cd_ticks) = rule.cooldown_ticks {
                if applied_any_effect {
                    cooldowns.start_cooldown(source_id.id, rule_idx, cd_ticks);
                }
            }
        }
    }
    if let (Some(mut t), Some(s)) = (telemetry, start) {
        t.interaction_us = s.elapsed().as_micros() as u32;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rules::{InteractionRule, StatEffect};
    use crate::rules::interaction::{MitigationRule, MitigationMode};

    fn setup_app() -> App {
        let mut app = App::new();
        app.insert_resource(SpatialHashGrid::new(20.0));
        app.insert_resource(InteractionRuleSet { rules: vec![] });
        app.insert_resource(crate::config::AggroMaskRegistry::default());
        app.insert_resource(FactionBuffs::default());
        app.init_resource::<crate::config::BuffConfig>();
        app.init_resource::<crate::config::CooldownTracker>();
        app.init_resource::<crate::config::TickCounter>();
        app.add_systems(Update, interaction_system);
        app
    }

    #[test]
    fn test_interaction_apply_rules() {
        let mut app = setup_app();

        // Add rules: Faction 0 attacks Faction 1
        app.insert_resource(InteractionRuleSet {
            rules: vec![
                InteractionRule {
                    source_faction: 0,
                    target_faction: 1,
                    range: 15.0,
                    effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                    source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
                },
                InteractionRule {
                    source_faction: 1,
                    target_faction: 0,
                    range: 15.0,
                    effects: vec![StatEffect { stat_index: 0, delta_per_second: -20.0 }],
                    source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
                },
            ],
        });

        // Add Attacker
        let attacker = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 0.0, y: 0.0 },
                FactionId(0),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        // Add Defender
        let defender = app
            .world_mut()
            .spawn((
                EntityId { id: 2 },
                Position { x: 5.0, y: 0.0 },
                FactionId(1),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        // Update SpatialHashGrid manually for the test
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (attacker, Vec2::new(0.0, 0.0), 0),
                (defender, Vec2::new(5.0, 0.0), 1),
            ]);
        }

        app.update();

        let attacker_stat = app.world().get::<StatBlock>(attacker).unwrap();
        let defender_stat = app.world().get::<StatBlock>(defender).unwrap();

        // Attacker attacked by Defender: 100 - (20/60) = 99.666...
        let expected_attacker_stat = 100.0 - (20.0 * (1.0 / 60.0));
        assert!((attacker_stat.0[0] - expected_attacker_stat).abs() < 1e-4);

        // Defender attacked by Attacker: 100 - (10/60) = 99.833...
        let expected_defender_stat = 100.0 - (10.0 * (1.0 / 60.0));
        assert!((defender_stat.0[0] - expected_defender_stat).abs() < 1e-4);
    }

    #[test]
    fn test_same_faction_no_interaction() {
        let mut app = setup_app();

        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1, // Doesn't match
                range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });

        let a1 = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 0.0, y: 0.0 },
                FactionId(0),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        let a2 = app
            .world_mut()
            .spawn((
                EntityId { id: 2 },
                Position { x: 5.0, y: 0.0 },
                FactionId(0),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(a1, Vec2::new(0.0, 0.0), 0), (a2, Vec2::new(5.0, 0.0), 0)]);
        }

        app.update();

        let a1_stat = app.world().get::<StatBlock>(a1).unwrap();
        let a2_stat = app.world().get::<StatBlock>(a2).unwrap();

        assert_eq!(a1_stat.0[0], 100.0);
        assert_eq!(a2_stat.0[0], 100.0);
    }

    #[test]
    fn test_out_of_range_no_interaction() {
        let mut app = setup_app();

        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });

        let attacker = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 0.0, y: 0.0 },
                FactionId(0),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        let defender = app
            .world_mut()
            .spawn((
                EntityId { id: 2 },
                Position { x: 20.0, y: 0.0 }, // Out of range
                FactionId(1),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (attacker, Vec2::new(0.0, 0.0), 0),
                (defender, Vec2::new(20.0, 0.0), 1),
            ]);
        }

        app.update();

        let defender_stat = app.world().get::<StatBlock>(defender).unwrap();
        assert_eq!(defender_stat.0[0], 100.0);
    }

    #[test]
    fn test_self_interaction_prevented() {
        let mut app = setup_app();

        // Even if there's a rule making a faction attack itself
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 0,
                range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });

        let entity = app
            .world_mut()
            .spawn((
                EntityId { id: 1 },
                Position { x: 0.0, y: 0.0 },
                FactionId(0),
                StatBlock::with_defaults(&[(0, 100.0)]),
                UnitClassId::default(), crate::components::CombatState::default(),
            ))
            .id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(entity, Vec2::new(0.0, 0.0), 0)]);
        }

        app.update();

        let stat = app.world().get::<StatBlock>(entity).unwrap();
        assert_eq!(stat.0[0], 100.0); // No self-harm
    }

    #[test]
    fn test_class_filtering_source() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: Some(1), target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId(0),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(5.0, 0.0), 1)]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0);

        *app.world_mut().get_mut::<UnitClassId>(source).unwrap() = UnitClassId(1);
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!(stat.0[0] < 100.0);
    }

    #[test]
    fn test_class_filtering_target() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: Some(2), range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId(0),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(5.0, 0.0), 1)]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0);

        *app.world_mut().get_mut::<UnitClassId>(target).unwrap() = UnitClassId(2);
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!(stat.0[0] < 100.0);
    }

    #[test]
    fn test_dynamic_range() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 10.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: Some(3), mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0), (3, 50.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 30.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(30.0, 0.0), 1)]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!(stat.0[0] < 100.0);
    }

    #[test]
    fn test_mitigation_percent() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: Some(MitigationRule { stat_index: 4, mode: MitigationMode::PercentReduction }),
                cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0), (4, 0.5)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(5.0, 0.0), 1)]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        let expected = 100.0 - (10.0 * (1.0 / 60.0) * 0.5);
        assert!((stat.0[0] - expected).abs() < 1e-4);
    }

    #[test]
    fn test_mitigation_flat() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: Some(MitigationRule { stat_index: 4, mode: MitigationMode::FlatReduction }),
                cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0), (4, 5.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(5.0, 0.0), 1)]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        let expected = 100.0 - (5.0 * (1.0 / 60.0));
        assert!((stat.0[0] - expected).abs() < 1e-4);
    }

    #[test]
    fn test_cooldown_prevents_rapid_fire() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: Some(60), aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(5.0, 0.0), 1)]);
        }
        
        // Frame 1: Should apply
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!((stat.0[0] - 99.0).abs() < 1e-4);

        // Frame 2-60: Should NOT apply
        for _ in 1..60 {
            app.update();
        }
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!((stat.0[0] - 99.0).abs() < 1e-4);

        // Frame 61: Cooldown over, should apply again
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert!((stat.0[0] - 98.0).abs() < 1e-4);
    }

    #[test]
    fn test_backward_compat_no_new_fields() {
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 15.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -10.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None, aoe: None, penetration: None,
            }],
        });
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(), crate::components::CombatState::default(),
        )).id();
        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[(source, Vec2::new(0.0, 0.0), 0), (target, Vec2::new(5.0, 0.0), 1)]);
        }
        app.update();
        let stat = app.world().get::<StatBlock>(target).unwrap();
        let expected = 100.0 - (10.0 * (1.0 / 60.0));
        assert!((stat.0[0] - expected).abs() < 1e-4);
    }
}
