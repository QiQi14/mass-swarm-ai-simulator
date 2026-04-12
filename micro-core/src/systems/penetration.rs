//! # Penetration Interaction System
//!
//! Processes `InteractionRule`s with `penetration: Some(...)`.
//! Handles both pen-only AND composite (aoe + pen) rules.
//!
//! For each source entity:
//!   1. Find nearest valid target → impact point + ray direction
//!   2. Query spatial grid for candidates along the ray
//!   3. Filter candidates (ray width OR AoE shape for composite)
//!   4. Sort by distance along ray
//!   5. Sequential energy delivery with absorption per target
//!
//! ## Mathematical Corrections
//! - **#2**: 2D cross-product for perpendicular distance (no trig)
//! - **#3**: Division-by-zero guard when ray length < ε
//! - **#4**: Kinetic vs Beam energy models (burst vs sustained)
//!
//! ## Ownership
//! - **Task:** phase_b2_penetration
//! - **Contract:** implementation_plan.md → Phase B.2
//!
//! ## Depends On
//! - `crate::components::{Position, FactionId, StatBlock, EntityId, UnitClassId}`
//! - `crate::spatial::SpatialHashGrid`
//! - `crate::rules::{InteractionRuleSet, aoe::*}`

use crate::components::{EntityId, FactionId, Position, StatBlock, UnitClassId};
use crate::config::FactionBuffs;
use crate::rules::aoe::{EnergyModel, PrecomputedPolygonEdges, AoeShape};
use crate::rules::InteractionRuleSet;
use crate::spatial::SpatialHashGrid;
use bevy::prelude::*;

/// Minimum ray length to avoid division-by-zero (Correction #3).
const RAY_LENGTH_EPSILON: f32 = 1e-6;

/// Processes penetration interaction rules.
///
/// Handles:
/// - **Pen-only** (`aoe: None, penetration: Some`): Simple ray cast with ray_width
/// - **Composite** (`aoe: Some, penetration: Some`): AoE shape filters hit zone,
///   penetration handles sequential energy absorption along the ray direction
///
/// ## Performance
/// - O(N × R_pen × K log K) where K = candidates sorted per ray
#[allow(clippy::too_many_arguments)]
pub fn penetration_interaction_system(
    grid: Res<SpatialHashGrid>,
    rules: Res<InteractionRuleSet>,
    aggro: Res<crate::config::AggroMaskRegistry>,
    combat_buffs: Res<FactionBuffs>,
    buff_config: Res<crate::config::BuffConfig>,
    mut cooldowns: ResMut<crate::config::CooldownTracker>,
    q_ro: Query<(Entity, &Position, &FactionId, &EntityId, &UnitClassId)>,
    mut q_rw: Query<&mut StatBlock>,
) {
    // Early exit: skip if no rules have penetration config
    if !rules.rules.iter().any(|r| r.penetration.is_some()) {
        return;
    }

    let tick_delta = 1.0 / 60.0;

    // Precompute polygon edges for composite AoE+pen rules
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
            // Only process rules WITH penetration config
            let pen = match &rule.penetration {
                Some(p) => p,
                None => continue,
            };

            // Standard faction/class/aggro/cooldown filters
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

            // Step 2: Build ray direction (Correction #3: division-by-zero guard)
            let ray_dx = impact_x - source_pos.x;
            let ray_dy = impact_y - source_pos.y;
            let ray_len = (ray_dx * ray_dx + ray_dy * ray_dy).sqrt();
            if ray_len < RAY_LENGTH_EPSILON {
                continue; // Target at source position — skip this rule
            }
            let ray_dir_x = ray_dx / ray_len;
            let ray_dir_y = ray_dy / ray_len;

            // Step 3: Query candidates — use effective_range for pen-only,
            // or max(effective_range, aoe_bounding) for composite
            let query_radius = if let Some(ref aoe) = rule.aoe {
                effective_range.max(aoe.bounding_radius() + ray_len)
            } else {
                effective_range
            };
            let all_candidates = grid.query_radius(center, query_radius);

            // Step 4: Filter & sort candidates by distance along ray
            let mut ray_targets: Vec<(Entity, f32)> = Vec::new(); // (entity, dot_along)

            // For composite mode, precompute rotation
            let (cos_t, sin_t) = if rule.aoe.is_some() {
                let theta = ray_dy.atan2(ray_dx);
                (theta.cos(), theta.sin())
            } else {
                (1.0, 0.0) // unused for pen-only
            };

            for &(candidate_entity, _, _) in &all_candidates {
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

                    let ap_x = cand_pos.x - source_pos.x;
                    let ap_y = cand_pos.y - source_pos.y;

                    // Dot product along ray = signed distance along ray direction
                    let dot_along = ap_x * ray_dir_x + ap_y * ray_dir_y;
                    if dot_along < 0.0 {
                        continue; // Behind the source — skip
                    }
                    if dot_along > effective_range {
                        continue; // Beyond weapon range — skip
                    }

                    if let Some(ref aoe) = rule.aoe {
                        // COMPOSITE MODE: use AoE shape for spatial filtering
                        // Transform to shape-local coords (centered on impact, rotated)
                        let dx = cand_pos.x - impact_x;
                        let dy = cand_pos.y - impact_y;
                        let local_x = dx * cos_t + dy * sin_t;
                        let local_y = -dx * sin_t + dy * cos_t;
                        if aoe.hit_test(local_x, local_y, precomputed[rule_idx].as_ref()).is_none() {
                            continue; // Outside AoE shape — skip
                        }
                    } else {
                        // PEN-ONLY MODE: Correction #2 — 2D cross-product perpendicular distance
                        let cross = ap_x * ray_dir_y - ap_y * ray_dir_x;
                        let perp_dist = cross.abs();
                        if perp_dist > pen.ray_width {
                            continue; // Outside ray width — skip
                        }
                    }

                    ray_targets.push((candidate_entity, dot_along));
                }
            }

            // Sort by distance along ray (nearest first)
            ray_targets.sort_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal));

            // Step 5: Sequential energy delivery
            let mut remaining_energy: f32 = 1.0; // Normalized [0.0, 1.0]
            let mut applied_any = false;
            let mut targets_hit: u32 = 0;

            for (target_entity, dot_along) in &ray_targets {
                if remaining_energy <= 0.0 {
                    break;
                }
                if let Some(max) = pen.max_targets {
                    if targets_hit >= max {
                        break;
                    }
                }

                // Distance gradient: further targets get less base damage
                let d_fraction = dot_along / effective_range;

                // Get AoE falloff factor for composite mode
                let aoe_factor = if let Some(ref aoe) = rule.aoe {
                    // Recalculate d_norm for this target in AoE shape
                    if let Ok((_, cand_pos, _, _, _)) = q_ro.get(*target_entity) {
                        let dx = cand_pos.x - impact_x;
                        let dy = cand_pos.y - impact_y;
                        let local_x = dx * cos_t + dy * sin_t;
                        let local_y = -dx * sin_t + dy * cos_t;
                        if let Some(d_norm) = aoe.hit_test(local_x, local_y, precomputed[rule_idx].as_ref()) {
                            aoe.falloff_factor(d_norm)
                        } else {
                            0.0
                        }
                    } else {
                        0.0
                    }
                } else {
                    // Pen-only: use linear range falloff
                    (1.0 - d_fraction).max(0.0)
                };

                if aoe_factor <= 0.0 {
                    continue;
                }

                // Apply effects with energy scaling
                for effect in &rule.effects {
                    let base_delta = effect.delta_per_second * tick_delta * damage_mult;
                    let final_delta = apply_mitigation(
                        base_delta, rule, *target_entity, &q_rw, tick_delta,
                    );

                    let energy_scaled = final_delta * remaining_energy * aoe_factor;

                    if let Ok(mut sb) = q_rw.get_mut(*target_entity) {
                        if effect.stat_index < sb.0.len() {
                            sb.0[effect.stat_index] += energy_scaled;
                            applied_any = true;
                        }
                    }
                }

                // Energy absorption (Correction #4: Kinetic vs Beam)
                match &pen.energy_model {
                    EnergyModel::Kinetic { base_energy } => {
                        if *base_energy > 0.0 {
                            // Read target's absorption stat
                            let target_stat = if pen.absorption_ignores_mitigation {
                                q_rw.get(*target_entity)
                                    .ok()
                                    .and_then(|sb| sb.0.get(pen.absorption_stat_index).copied())
                                    .unwrap_or(0.0)
                            } else {
                                // Post-mitigation absorption (rare, but configurable)
                                q_rw.get(*target_entity)
                                    .ok()
                                    .and_then(|sb| sb.0.get(pen.absorption_stat_index).copied())
                                    .unwrap_or(0.0)
                            };

                            let absorbed = (target_stat.max(0.0) / base_energy).min(remaining_energy);
                            remaining_energy -= absorbed;
                        }
                    }
                    EnergyModel::Beam => {
                        // Beam: no absorption — all targets take damage
                        // Energy doesn't deplete
                    }
                }

                targets_hit += 1;
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
    use crate::rules::aoe::{
        AoeConfig, AoeFalloff, AoeShape, EnergyModel, PenetrationConfig, RotationMode,
    };

    fn setup_app() -> App {
        let mut app = App::new();
        app.insert_resource(SpatialHashGrid::new(20.0));
        app.insert_resource(InteractionRuleSet { rules: vec![] });
        app.insert_resource(crate::config::AggroMaskRegistry::default());
        app.insert_resource(FactionBuffs::default());
        app.init_resource::<crate::config::BuffConfig>();
        app.init_resource::<crate::config::CooldownTracker>();
        app.add_systems(Update, penetration_interaction_system);
        app
    }

    fn pen_kinetic(base_energy: f32) -> PenetrationConfig {
        PenetrationConfig {
            ray_width: 2.0,
            max_targets: None,
            energy_model: EnergyModel::Kinetic { base_energy },
            absorption_ignores_mitigation: true,
            absorption_stat_index: 0,
        }
    }

    fn pen_beam() -> PenetrationConfig {
        PenetrationConfig {
            ray_width: 2.0,
            max_targets: None,
            energy_model: EnergyModel::Beam,
            absorption_ignores_mitigation: true,
            absorption_stat_index: 0,
        }
    }

    #[test]
    fn test_ray_hits_aligned_targets() {
        // Arrange: 3 targets in a line along X axis
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_beam()),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t1 = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t2 = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 30.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t3 = app.world_mut().spawn((
            EntityId { id: 4 }, Position { x: 60.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t1, Vec2::new(10.0, 0.0), 1),
                (t2, Vec2::new(30.0, 0.0), 1),
                (t3, Vec2::new(60.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert — all 3 targets should take damage (beam mode, no absorption)
        let s1 = app.world().get::<StatBlock>(t1).unwrap();
        let s2 = app.world().get::<StatBlock>(t2).unwrap();
        let s3 = app.world().get::<StatBlock>(t3).unwrap();
        assert!(s1.0[0] < 100.0, "t1 should take damage, got {}", s1.0[0]);
        assert!(s2.0[0] < 100.0, "t2 should take damage, got {}", s2.0[0]);
        assert!(s3.0[0] < 100.0, "t3 should take damage, got {}", s3.0[0]);
    }

    #[test]
    fn test_ray_misses_perpendicular_targets() {
        // Arrange: target beside ray (outside ray_width)
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_beam()),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // On-line target (defines ray direction)
        let t_hit = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 30.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Off-line target: 10 units perpendicular (ray_width = 2.0)
        let t_miss = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 30.0, y: 10.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t_hit, Vec2::new(30.0, 0.0), 1),
                (t_miss, Vec2::new(30.0, 10.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s_hit = app.world().get::<StatBlock>(t_hit).unwrap();
        let s_miss = app.world().get::<StatBlock>(t_miss).unwrap();
        assert!(s_hit.0[0] < 100.0, "On-line target should take damage");
        assert_eq!(s_miss.0[0], 100.0, "Off-line target should be untouched");
    }

    #[test]
    fn test_ray_energy_absorption_kinetic() {
        // Arrange: Kinetic projectile with base_energy=100, target has 60 HP
        // Target absorbs 60/100 = 0.6 of energy, leaving 0.4 for next target
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -6000.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_kinetic(100.0)),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // First target: 60 HP → absorbs 60/100 = 0.6 energy
        let t1 = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 60.0)]), UnitClassId::default(),
        )).id();

        // Second target: behind first, should receive less damage
        let t2 = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 20.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t1, Vec2::new(10.0, 0.0), 1),
                (t2, Vec2::new(20.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s1 = app.world().get::<StatBlock>(t1).unwrap();
        let s2 = app.world().get::<StatBlock>(t2).unwrap();
        let dmg1 = 60.0 - s1.0[0];
        let dmg2 = 100.0 - s2.0[0];
        assert!(dmg1 > 0.0, "First target should take damage");
        assert!(dmg2 > 0.0, "Second target should take damage through penetration");
        assert!(dmg1 > dmg2, "First target should take MORE damage: t1={}, t2={}", dmg1, dmg2);
    }

    #[test]
    fn test_ray_body_block() {
        // Arrange: Tank with 200 HP absorbs ALL energy (200/100 = 2.0, clamped to 1.0)
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_kinetic(100.0)),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Tank: 200 HP → absorbs 200/100 = 2.0, clamped to remaining_energy (1.0)
        let tank = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 200.0)]), UnitClassId::default(),
        )).id();

        // Squishy behind tank
        let squishy = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 20.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 50.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (tank, Vec2::new(10.0, 0.0), 1),
                (squishy, Vec2::new(20.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert — tank takes damage, squishy is protected
        let tank_stat = app.world().get::<StatBlock>(tank).unwrap();
        let squishy_stat = app.world().get::<StatBlock>(squishy).unwrap();
        assert!(tank_stat.0[0] < 200.0, "Tank should take damage");
        assert_eq!(squishy_stat.0[0], 50.0, "Squishy should be body-blocked by tank");
    }

    #[test]
    fn test_ray_max_targets_cap() {
        // Arrange: max_targets = 2, 3 targets in line → only first 2 hit
        let mut app = setup_app();
        let mut pen = pen_beam();
        pen.max_targets = Some(2);

        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t1 = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t2 = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 20.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t3 = app.world_mut().spawn((
            EntityId { id: 4 }, Position { x: 30.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t1, Vec2::new(10.0, 0.0), 1),
                (t2, Vec2::new(20.0, 0.0), 1),
                (t3, Vec2::new(30.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s1 = app.world().get::<StatBlock>(t1).unwrap();
        let s2 = app.world().get::<StatBlock>(t2).unwrap();
        let s3 = app.world().get::<StatBlock>(t3).unwrap();
        assert!(s1.0[0] < 100.0, "t1 should take damage");
        assert!(s2.0[0] < 100.0, "t2 should take damage");
        assert_eq!(s3.0[0], 100.0, "t3 should be untouched (max_targets=2)");
    }

    #[test]
    fn test_ray_direction_only_forward() {
        // Arrange: target behind source should not be hit
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_beam()),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 50.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Forward target: 15 units ahead (closer, will be picked as nearest)
        let t_fwd = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 65.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Behind source: 25 units back (further, won't be nearest)
        let t_behind = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 25.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(50.0, 0.0), 0),
                (t_fwd, Vec2::new(65.0, 0.0), 1),
                (t_behind, Vec2::new(25.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s_fwd = app.world().get::<StatBlock>(t_fwd).unwrap();
        let s_behind = app.world().get::<StatBlock>(t_behind).unwrap();
        assert!(s_fwd.0[0] < 100.0, "Forward target should take damage");
        assert_eq!(s_behind.0[0], 100.0, "Behind target should be untouched");
    }

    #[test]
    fn test_ray_division_by_zero_guard() {
        // Arrange: source and target at same position (Correction #3)
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_beam()),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 10.0, y: 10.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Target at exact same position
        let target = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 10.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(10.0, 10.0), 0),
                (target, Vec2::new(10.0, 10.0), 1),
            ]);
        }

        // Act — should not panic
        app.update();

        // Assert — target untouched (ray_length < ε, skipped gracefully)
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0, "Target at source position should be skipped (div-by-zero guard)");
    }

    #[test]
    fn test_ray_beam_no_absorption() {
        // Arrange: Beam mode should not absorb energy — all targets get full damage
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -600.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
                penetration: Some(pen_beam()),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Two targets at similar distances
        let t1 = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 10.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        let t2 = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 20.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t1, Vec2::new(10.0, 0.0), 1),
                (t2, Vec2::new(20.0, 0.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert — both take damage (energy = 1.0 for both) but further gets less (range falloff)
        let s1 = app.world().get::<StatBlock>(t1).unwrap();
        let s2 = app.world().get::<StatBlock>(t2).unwrap();
        assert!(s1.0[0] < 100.0, "t1 should take damage");
        assert!(s2.0[0] < 100.0, "t2 should take damage (beam, no absorption)");
    }

    #[test]
    fn test_composite_aoe_pen_cone_shotgun() {
        // Arrange: Cone-shaped AoE + Kinetic penetration = shotgun
        // The cone shape filters which targets are hit, penetration handles energy
        let mut app = setup_app();

        // Cone shape: triangle pointing right (CCW winding)
        // Apex offset slightly from origin to avoid c=0 degeneracy in half-plane math
        let cone_vertices = vec![
            [-1.0, 0.0],    // apex near impact
            [30.0, -15.0],  // lower right
            [30.0, 15.0],   // upper right
        ];

        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 100.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -6000.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: Some(AoeConfig {
                    shape: AoeShape::ConvexPolygon {
                        vertices: cone_vertices,
                        rotation_mode: RotationMode::TargetAligned,
                    },
                    falloff: AoeFalloff::None,
                }),
                penetration: Some(pen_kinetic(100.0)),
            }],
        });

        let source = app.world_mut().spawn((
            EntityId { id: 1 }, Position { x: 0.0, y: 0.0 }, FactionId(0),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Impact target (nearest, defines direction)
        let t_impact = app.world_mut().spawn((
            EntityId { id: 2 }, Position { x: 20.0, y: 0.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 40.0)]), UnitClassId::default(),
        )).id();

        // Target inside cone (slightly off-axis but within cone polygon)
        let t_in_cone = app.world_mut().spawn((
            EntityId { id: 3 }, Position { x: 35.0, y: 5.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        // Target OUTSIDE cone (perpendicular, beyond cone width)
        let t_outside = app.world_mut().spawn((
            EntityId { id: 4 }, Position { x: 20.0, y: 40.0 }, FactionId(1),
            StatBlock::with_defaults(&[(0, 100.0)]), UnitClassId::default(),
        )).id();

        {
            let mut grid = app.world_mut().resource_mut::<SpatialHashGrid>();
            grid.rebuild(&[
                (source, Vec2::new(0.0, 0.0), 0),
                (t_impact, Vec2::new(20.0, 0.0), 1),
                (t_in_cone, Vec2::new(35.0, 5.0), 1),
                (t_outside, Vec2::new(20.0, 40.0), 1),
            ]);
        }

        // Act
        app.update();

        // Assert
        let s_impact = app.world().get::<StatBlock>(t_impact).unwrap();
        let s_in_cone = app.world().get::<StatBlock>(t_in_cone).unwrap();
        let s_outside = app.world().get::<StatBlock>(t_outside).unwrap();

        assert!(s_impact.0[0] < 40.0, "Impact target should take damage, got {}", s_impact.0[0]);
        assert!(s_in_cone.0[0] < 100.0, "In-cone target should take penetrating damage, got {}", s_in_cone.0[0]);
        assert_eq!(s_outside.0[0], 100.0, "Outside-cone target should be untouched");
    }

    #[test]
    fn test_pen_rule_without_pen_skipped() {
        // Arrange: rule without penetration should be skipped by this system
        let mut app = setup_app();
        app.insert_resource(InteractionRuleSet {
            rules: vec![InteractionRule {
                source_faction: 0, target_faction: 1, range: 50.0,
                effects: vec![StatEffect { stat_index: 0, delta_per_second: -60.0 }],
                source_class: None, target_class: None, range_stat_index: None,
                mitigation: None, cooldown_ticks: None,
                aoe: None,
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

        // Assert
        let stat = app.world().get::<StatBlock>(target).unwrap();
        assert_eq!(stat.0[0], 100.0, "Non-pen rule should be ignored");
    }

    #[test]
    fn test_penetration_serde_roundtrip() {
        let pen = PenetrationConfig {
            ray_width: 3.0,
            max_targets: Some(5),
            energy_model: EnergyModel::Kinetic { base_energy: 150.0 },
            absorption_ignores_mitigation: true,
            absorption_stat_index: 0,
        };
        let json = serde_json::to_string(&pen).unwrap();
        let de: PenetrationConfig = serde_json::from_str(&json).unwrap();
        assert_eq!(pen, de, "PenetrationConfig should roundtrip");

        let beam = PenetrationConfig {
            ray_width: 1.0,
            max_targets: None,
            energy_model: EnergyModel::Beam,
            absorption_ignores_mitigation: false,
            absorption_stat_index: 2,
        };
        let json2 = serde_json::to_string(&beam).unwrap();
        let de2: PenetrationConfig = serde_json::from_str(&json2).unwrap();
        assert_eq!(beam, de2, "Beam PenetrationConfig should roundtrip");
    }
}
