//! # ZMQ Reset Handler
//!
//! Processes `ResetEnvironment` requests from the Python macro-brain.
//! Despawns all entities, applies terrain/combat/ability config, and respawns.
//!
//! ## Ownership
//! - **Task:** task_r1_split_zmq_systems
//! - **Contract:** implementation_plan.md → Task R1
//!
//! ## Depends On
//! - `crate::components::*`
//! - `crate::config::*`
//! - `crate::terrain::TerrainGrid`

use bevy::prelude::*;
use rand::Rng;

use crate::bridges::zmq_protocol::{SpawnConfig, TerrainPayload};
use crate::components::{
    EntityId, FactionId, MovementConfig, NextEntityId, Position, StatBlock, Velocity, VisionRadius,
    UnitClassId,
};
use crate::config::{ActiveSubFactions, ActiveZoneModifiers, AggroMaskRegistry, TickCounter};
use crate::rules::NavigationRuleSet;
use crate::systems::directive_executor::LatestDirective;
use crate::terrain::TerrainGrid;

/// Queues a pending environment reset from `ai_poll_system`.
/// Consumed by `reset_environment_system` on the next tick.
#[derive(Resource, Debug, Default)]
pub struct PendingReset {
    pub request: Option<ResetRequest>,
}

/// Data payload for an environment reset.
#[derive(Debug, Clone)]
pub struct ResetRequest {
    pub terrain: Option<TerrainPayload>,
    pub spawns: Vec<SpawnConfig>,
    pub combat_rules: Option<Vec<crate::bridges::zmq_protocol::CombatRulePayload>>,
    pub ability_config: Option<crate::bridges::zmq_protocol::AbilityConfigPayload>,
    pub movement_config: Option<crate::bridges::zmq_protocol::MovementConfigPayload>,
    pub max_density: Option<f32>,
    pub terrain_thresholds: Option<crate::bridges::zmq_protocol::TerrainThresholdsPayload>,
    pub removal_rules: Option<Vec<crate::bridges::zmq_protocol::RemovalRulePayload>>,
    pub navigation_rules: Option<Vec<crate::bridges::zmq_protocol::NavigationRulePayload>>,
}

/// Processes queued environment resets from `ai_poll_system`.
///
/// On reset:
/// 1. Despawns ALL entities with `EntityId` (complete world wipe)
/// 2. Applies new terrain if provided
/// 3. Resets tick counter, zone modifiers, speed buffs, aggro masks, sub-factions
/// 4. Spawns new entities per the `spawns` configuration
///
/// This ensures training episodes start with a clean, deterministic state.
#[derive(bevy::ecs::system::SystemParam)]
pub(crate) struct ResetRules<'w> {
    nav: ResMut<'w, NavigationRuleSet>,
    behavior: ResMut<'w, crate::rules::FactionBehaviorMode>,
    interaction: ResMut<'w, crate::rules::InteractionRuleSet>,
    removal: ResMut<'w, crate::rules::RemovalRuleSet>,
}

#[allow(clippy::too_many_arguments)]
pub(crate) fn reset_environment_system(
    mut commands: Commands,
    mut pending: ResMut<PendingReset>,
    entity_query: Query<Entity, With<EntityId>>,
    mut next_id: ResMut<NextEntityId>,
    mut tick: ResMut<TickCounter>,
    mut terrain: ResMut<TerrainGrid>,
    mut zones: ResMut<ActiveZoneModifiers>,
    mut faction_buffs: ResMut<crate::config::FactionBuffs>,
    mut aggro: ResMut<AggroMaskRegistry>,
    mut sub_factions: ResMut<ActiveSubFactions>,
    mut latest_directive: ResMut<LatestDirective>,
    mut buff_config: ResMut<crate::config::BuffConfig>,
    mut density_config: ResMut<crate::config::DensityConfig>,
    mut cooldowns: ResMut<crate::config::CooldownTracker>,
    mut rules: ResetRules,
    training_mode: Res<crate::config::TrainingMode>,
) {
    let Some(reset) = pending.request.take() else {
        return;
    };

    // 1. Despawn ALL entities
    let mut despawn_count = 0u32;
    for entity in entity_query.iter() {
        commands.entity(entity).despawn();
        despawn_count += 1;
    }

    // 2. Apply terrain if provided
    if let Some(tp) = &reset.terrain {
        *terrain = TerrainGrid {
            width: tp.width,
            height: tp.height,
            cell_size: tp.cell_size,
            hard_costs: tp.hard_costs.clone(),
            soft_costs: tp.soft_costs.clone(),
            destructible_min: 60000,
            impassable_threshold: 65535,
        };
    }

    // 3. Reset game state
    tick.tick = 0;
    zones.zones.clear();
    cooldowns.cooldowns.clear();
    *faction_buffs = Default::default();
    aggro.masks.clear();
    sub_factions.factions.clear();
    rules.nav.rules.clear();
    // Apply navigation rules from game profile (if provided)
    if let Some(nav_rules) = &reset.navigation_rules {
        for r in nav_rules {
            rules.nav.rules.push(crate::rules::NavigationRule {
                follower_faction: r.follower_faction,
                target: r.target.clone(),
            });
        }
        if !training_mode.0 {
            println!(
                "[Reset] Applied {} navigation rules from game profile",
                rules.nav.rules.len()
            );
        }
    } else if !training_mode.0 {
        println!(
            "[Reset] WARNING: No navigation_rules provided. Factions will not navigate. \
                  The adapter (game profile) should provide explicit navigation rules."
        );
    }
    // Clear static mode so ALL factions follow flow fields during training
    rules.behavior.static_factions.clear();
    latest_directive.directives.clear();
    next_id.0 = 1;

    // 4. Spawn new entities per config
    let mut rng = rand::rng();
    let mut total_spawned = 0u32;
    for spawn in &reset.spawns {
        // Build stat defaults from spawn config — adapter MUST provide explicit values
        let stat_defaults: Vec<(usize, f32)> = if spawn.stats.is_empty() {
            if !training_mode.0 {
                println!(
                    "[Reset] WARNING: SpawnConfig for faction_{} has empty stats. \
                     Entities will spawn with all-zero StatBlock. \
                     The adapter (game profile) should provide explicit stat values.",
                    spawn.faction_id
                );
            }
            vec![]
        } else {
            spawn.stats.iter().map(|e| (e.index, e.value)).collect()
        };

        for _ in 0..spawn.count {
            let entity_id = EntityId { id: next_id.0 };
            next_id.0 += 1;

            // Spread around the spawn center
            let angle: f32 = rng.random_range(0.0..std::f32::consts::TAU);
            let radius: f32 = rng.random_range(0.0..spawn.spread);
            let x = spawn.x + angle.cos() * radius;
            let y = spawn.y + angle.sin() * radius;

            commands.spawn((
                entity_id,
                Position { x, y },
                Velocity { dx: 0.0, dy: 0.0 },
                FactionId(spawn.faction_id),
                StatBlock::with_defaults(&stat_defaults),
                VisionRadius::default(),
                UnitClassId(spawn.unit_class_id),
                if let Some(ref mc) = reset.movement_config {
                    MovementConfig {
                        max_speed: mc.max_speed,
                        steering_factor: mc.steering_factor,
                        separation_radius: mc.separation_radius,
                        separation_weight: mc.separation_weight,
                        flow_weight: mc.flow_weight,
                    }
                } else {
                    MovementConfig::default()
                },
            ));
            total_spawned += 1;
        }
    }

    // 5. Apply combat rules from game profile (if provided)
    if let Some(crules) = &reset.combat_rules {
        rules.interaction.rules.clear();
        for r in crules {
            rules.interaction.rules.push(crate::rules::InteractionRule {
                source_faction: r.source_faction,
                target_faction: r.target_faction,
                range: r.range,
                effects: r
                    .effects
                    .iter()
                    .map(|e| crate::rules::StatEffect {
                        stat_index: e.stat_index,
                        delta_per_second: e.delta_per_second,
                    })
                    .collect(),
                source_class: r.source_class,
                target_class: r.target_class,
                range_stat_index: r.range_stat_index,
                mitigation: r.mitigation.as_ref().map(|m| crate::rules::interaction::MitigationRule {
                    stat_index: m.stat_index,
                    mode: match m.mode.as_str() {
                        "FlatReduction" => crate::rules::interaction::MitigationMode::FlatReduction,
                        _ => crate::rules::interaction::MitigationMode::PercentReduction,
                    },
                }),
                cooldown_ticks: r.cooldown_ticks,
            });
        }
        if !training_mode.0 {
            println!(
                "[Reset] Applied {} combat rules from game profile",
                rules.interaction.rules.len()
            );
        }
    }

    // 6. Apply new Reset properties
    if let Some(cfg) = &reset.ability_config {
        buff_config.cooldown_ticks = cfg.buff_cooldown_ticks;
        buff_config.movement_speed_stat = cfg.movement_speed_stat;
        buff_config.combat_damage_stat = cfg.combat_damage_stat;
        buff_config.zone_modifier_duration_ticks = cfg.zone_modifier_duration_ticks;
    }
    if let Some(den) = reset.max_density {
        density_config.max_density = den;
    }
    if let Some(tt) = &reset.terrain_thresholds {
        terrain.impassable_threshold = tt.impassable_threshold;
        terrain.destructible_min = tt.destructible_min;
    }
    if let Some(rr) = &reset.removal_rules {
        rules.removal.rules.clear();
        for r in rr {
            rules.removal.rules.push(crate::rules::RemovalRule {
                stat_index: r.stat_index,
                threshold: r.threshold,
                condition: match r.condition.as_str() {
                    "LessThanEqual" => crate::rules::RemovalCondition::LessOrEqual,
                    "GreaterThanEqual" => crate::rules::RemovalCondition::GreaterOrEqual,
                    _ => crate::rules::RemovalCondition::LessOrEqual,
                },
            });
        }
    }

    if !training_mode.0 {
        println!(
            "[Reset] Despawned {} entities, spawned {} new entities",
            despawn_count, total_spawned
        );
    }
}
