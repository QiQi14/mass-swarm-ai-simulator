//! # AoE Interaction System
//!
//! Processes `InteractionRule`s with `aoe: Some(...)` and NO penetration.
//! (Composite aoe+penetration rules are handled by `penetration_system`.)
//!
//! For each source entity:
//!   1. Find nearest valid target within `range` → impact point
//!   2. Query spatial grid for ALL targets within AoE shape's bounding radius
//!   3. Apply damage × falloff_factor(d_norm) to each target inside the shape
//!
//! Runs after `interaction_system` to avoid double-processing.
//!
//! ## Ownership
//! - **Task:** phase_b1_aoe_damage
//! - **Contract:** implementation_plan.md → Phase B.1
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, StatBlock, EntityId, UnitClassId}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::rules::{InteractionRuleSet, aoe::*}`

use crate::components::{EntityId, FactionId, Position, StatBlock, UnitClassId};
use crate::config::FactionBuffs;
use crate::rules::aoe::{PrecomputedPolygonEdges, RotationMode, AoeShape};
use crate::rules::InteractionRuleSet;
use crate::spatial::SpatialHashGrid;
use bevy::prelude::*;

/// Processes AoE-only interaction rules (aoe: Some, penetration: None).
///
/// ## Flow
/// 1. Filter: only rules with `aoe` config
/// 2. Find nearest valid target → impact center
/// 3. Transform candidates to shape-local coordinates
/// 4. Hit-test + gradient → apply scaled damage
///
/// ## Performance
/// - O(N × R_aoe × K) where R_aoe = AoE rules only
/// - Polygon precomputation is per-rule, cached per system run
/// - No Vec/HashMap allocations beyond spatial grid query
#[allow(clippy::too_many_arguments)]
pub fn aoe_interaction_system(
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    aggro: Res<crate::config::AggroMaskRegistry>,
    combat_buffs: Res<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    mut cooldowns: ResMut<crate::config::CooldownTracker>,
    q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
    mut q_rw: Query<&mut StatBlock>,
) {
    // Early exit: skip if no rules are AoE-only (aoe present, no penetration)
    if !rules.rules.iter().any(|r| r.aoe.is_some() && r.penetration.is_none()) {
        return;
    }

    let tick_delta = 1.0 / 60.0;

    // Precompute polygon edges for all AoE rules (once per tick)
    let precomputed: Vec<Option<PrecomputedPolygonEdges>> = rules
        .rules
        .iter()
        .map(|r| {
            r.aoe.as_ref().and_then(|aoe| match &aoe.shape {
                AoeShape::ConvexPolygon { vertices, .. } => {
                    Some(PrecomputedPolygonEdges::from_vertices(vertices))
                }
                _ => None,
            })
        })
        .collect();

    for (source_entity, source_pos, source_faction, source_id, source_class) in q_ro.iter() {
        for (rule_idx, rule) in rules.rules.iter().enumerate() {
            // Only process AoE-only rules (skip composite aoe+pen → penetration_system)
            if rule.penetration.is_some() {
                continue;
            }
            let aoe = match &rule.aoe {
                Some(a) => a,
                None => continue,
            };

            // Standard faction/class/aggro/cooldown filters (same as interaction_system)
            if rule.source_faction != source_faction.0 {
                continue;
            }
            if let Some(rc) = rule.source_class {
                if source_class.0 != rc {
                    continue;
                }
            }
            if !aggro.is_combat_allowed(rule.source_faction, rule.target_faction) {
                continue;
            }
            if rule.cooldown_ticks.is_some() && !cooldowns.can_fire(source_id.id, rule_idx) {
                continue;
            }

            let effective_range = rule
                .range_stat_index
                .and_then(|idx| q_rw.get(source_entity).ok()?.0.get(idx).copied())
                .unwrap_or(rule.range);

            let damage_mult = buff_config
                .combat_damage_stat
                .map(|si| combat_buffs.get_multiplier(source_faction.0, source_id.id, si))
                .unwrap_or(1.0);

            // Step 1: Find nearest valid target → impact point
            let center = Vec2::new(source_pos.x, source_pos.y);
            let neighbors = grid.query_radius(center, effective_range);

            let impact = find_nearest_target(
                &neighbors,
                source_entity,
                rule.target_faction,
                rule.target_class,
                &q_ro,
                source_pos,
            );
            let (impact_x, impact_y) = match impact {
                Some(v) => v,
                None => continue,
            };

            // Step 2: Calculate rotation angle for oriented shapes
            let theta = match aoe.rotation_mode() {
                RotationMode::TargetAligned => {
                    (impact_y - source_pos.y).atan2(impact_x - source_pos.x)
                }
                RotationMode::Fixed(angle) => *angle,
            };
            let cos_t = theta.cos();
            let sin_t = theta.sin();

            // Step 3: Query splash zone — use shape's bounding radius
            let splash_radius = aoe.bounding_radius();
            let splash_center = Vec2::new(impact_x, impact_y);
            let splash_candidates = grid.query_radius(splash_center, splash_radius);

            let mut applied_any = false;

            for &(candidate_entity, _, _) in &splash_candidates {
                if candidate_entity == source_entity {
                    continue;
                }
                if let Ok((_, cand_pos, cand_faction, _, cand_class)) =
                    q_ro.get(candidate_entity)
                {
                    if cand_faction.0 != rule.target_faction {
                        continue;
                    }
                    if let Some(rc) = rule.target_class {
                        if cand_class.0 != rc {
                            continue;
                        }
                    }

                    // Transform to shape-local coordinates (centered on impact, rotated by -theta)
                    let dx = cand_pos.x - impact_x;
                    let dy = cand_pos.y - impact_y;
                    let local_x = dx * cos_t + dy * sin_t;
                    let local_y = -dx * sin_t + dy * cos_t;

                    // Hit-test + gradient computation
                    if let Some(d_norm) =
                        aoe.hit_test(local_x, local_y, precomputed[rule_idx].as_ref())
                    {
                        let factor = aoe.falloff_factor(d_norm);
                        if factor <= 0.0 {
                            continue;
                        }

                        for effect in &rule.effects {
                            let base_delta = effect.delta_per_second * tick_delta * damage_mult;
                            let final_delta =
                                apply_mitigation(base_delta, rule, candidate_entity, &q_rw, tick_delta);

                            if let Ok(mut sb) = q_rw.get_mut(candidate_entity) {
                                if effect.stat_index < sb.0.len() {
                                    sb.0[effect.stat_index] += final_delta * factor;
                                    applied_any = true;
                                }
                            }
                        }
                    }
                }
            }

            if let Some(cd) = rule.cooldown_ticks {
                if applied_any {
                    cooldowns.start_cooldown(source_id.id, rule_idx, cd);
                }
            }
        }
    }
}

/// Find the nearest valid target entity, returns (x, y) of impact point.
fn find_nearest_target(
    neighbors: &[(Entity, Vec2, u32)],
    source_entity: Entity,
    target_faction: u32,
    target_class: Option<u32>,
    q_ro: &Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
    source_pos: &Position,
) -> Option<(f32, f32)> {
    let mut best: Option<(f32, f32, f32)> = None; // (x, y, dist_sq)

    for &(entity, _, _) in neighbors {
        if entity == source_entity {
            continue;
        }
        if let Ok((_, pos, faction, _, class)) = q_ro.get(entity) {
            if faction.0 != target_faction {
                continue;
            }
            if let Some(rc) = target_class {
                if class.0 != rc {
                    continue;
                }
            }
            let dx = pos.x - source_pos.x;
            let dy = pos.y - source_pos.y;
            let dist_sq = dx * dx + dy * dy;
            if best.is_none() || dist_sq < best.unwrap().2 {
                best = Some((pos.x, pos.y, dist_sq));
            }
        }
    }

    best.map(|(x, y, _)| (x, y))
}

/// Apply mitigation to base_delta, respecting the rule's mitigation config.
fn apply_mitigation(
    base_delta: f32,
    rule: &crate::rules::InteractionRule,
    target_entity: Entity,
    q_rw: &Query<&mut StatBlock>,
    tick_delta: f32,
) -> f32 {
    if let Some(ref mit) = rule.mitigation {
        let mit_value = q_rw
            .get(target_entity)
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
    }
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rules::{InteractionRule, StatEffect};
    use crate::rules::aoe::{AoeConfig, AoeFalloff, AoeShape, RotationMode};

    fn setup_app() -> App {
        let mut app = App::new();
        app.insert_resource(SpatialHashGrid::new(20.0));
        app.insert_resource(InteractionRuleSet { rules: vec![] });
        app.insert_resource(crate::config::AggroMaskRegistry::default());
        app.insert_resource(FactionBuffs::default());
        app.init_resource::<crate::config::BuffConfig>();
        app.init_resource::<crate::config::CooldownTracker>();
        app.add_systems(Update, aoe_interaction_system);
        app
    }

    #[test]
    fn test_aoe_circle_damages_all_in_radius() {
        // Arrange
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 50.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
                aoe: Some(AoeConfig {
                    shape: AoeShape::Circle { radius: 20.0 },
                    falloff: AoeFalloff::None,
                }),
                penetration: None,
            }],
        });

        // Source at origin
        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Target 1: at (10, 0) — nearest, will be impact center
        let t1 = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Target 2: at (15, 0) — within AoE radius (20) from impact (10,0)
        let t2 = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 15.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Target 3: at (40, 0) — outside AoE radius (20) from impact (10,0)
        let t3 = app.world_mut().spawn((
            EntityId { id: 4 }, Position { x: 40.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t1, Vec2::new(10.0, 0.0), 1),
                (t2, Vec2::new(15.0, 0.0), 1),
                (t3, Vec2::new(40.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s1 = app.world().get::<StatBlock>(t1).unwrap();
        let s2 = app.world().get::<StatBlock>(t2).unwrap();
        let s3 = app.world().get::<StatBlock>(t3).unwrap();
        assert!(s1.0[0] < 100.0, "t1 should take damage (at impact center), got {}", s1.0[0]);
        assert!(s2.0[0] < 100.0, "t2 should take damage (within AoE), got {}", s2.0[0]);
        assert_eq!(s3.0[0], 100.0, "t3 should be untouched (outside AoE)");
    }

    #[test]
    fn test_aoe_circle_gradient_center_vs_edge() {
        // Arrange
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 50.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
                aoe: Some(AoeConfig {
                    shape: AoeShape::Circle { radius: 20.0 },
                    falloff: AoeFalloff::Linear,
                }),
                penetration: None,
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Impact target at (10, 0)
        let center_target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Edge target at (25, 0) — 15 units from impact, d_norm = 15/20 = 0.75
        let edge_target = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 25.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (center_target, Vec2::new(10.0, 0.0), 1),
                (edge_target, Vec2::new(25.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let center_stat = app.world().get::<StatBlock>(center_target).unwrap();
        let edge_stat = app.world().get::<StatBlock>(edge_target).unwrap();

        let center_dmg = 100.0 - center_stat.0[0];
        let edge_dmg = 100.0 - edge_stat.0[0];
        assert!(
            center_dmg > edge_dmg,
            "Center target should take MORE damage than edge: center={}, edge={}",
            center_dmg, edge_dmg
        );
    }

    #[test]
    fn test_aoe_no_self_damage() {
        // Arrange
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 50.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
                aoe: Some(AoeConfig {
                    shape: AoeShape::Circle { radius: 100.0 },
                    falloff: AoeFalloff::None,
                }),
                penetration: None,
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (target, Vec2::new(5.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert - source should be untouched (even though inside AoE radius)
        let source_stat = app.world().get::<StatBlock>(source).unwrap();
        assert_eq!(source_stat.0[0], 100.0, "Source should not damage itself");
    }

    #[test]
    fn test_aoe_rule_without_aoe_skipped() {
        // Arrange — rule WITHOUT aoe config should NOT be processed by aoe_interaction_system
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 50.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
                aoe: None, penetration: None, // No AoE — this system should skip it
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 5.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (target, Vec2::new(5.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert - target untouched because the rule has no AoE and this system skips it
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0, "Non-AoE rule should be ignored by AoE system");
    }

    #[test]
    fn test_aoe_with_fixed_rotation() {
        // Arrange — ellipse with fixed rotation
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0,
                target_faction: 1,
                range: 50.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None, mitigation: None, cooldown_ticks: None,
                aoe: Some(AoeConfig {
                    shape: AoeShape::Ellipse {
                        semi_major: 30.0,
                        semi_minor: 5.0,
                        rotation_mode: RotationMode::Fixed(0.0), // Horizontal
                    },
                    falloff: AoeFalloff::None,
                }),
                penetration: None,
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Impact at (10, 0) — nearest target
        let t_impact = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // This one is 10 units directly above impact — outside minor axis (5.0)
        let t_above = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 10.0, y: 10.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t_impact, Vec2::new(10.0, 0.0), 1),
                (t_above, Vec2::new(10.0, 10.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s_impact = app.world().get::<StatBlock>(t_impact).unwrap();
        let s_above = app.world().get::<StatBlock>(t_above).unwrap();
        assert!(s_impact.0[0] < 100.0, "Impact target should take damage");
        assert_eq!(s_above.0[0], 100.0, "Target above should miss (outside minor axis)");
    }
}
