//! # Directive Executor
//!
//! Processes `MacroDirective` commands from the Python macro-brain.
//! Maps directives to ECS state mutations (navigation, buffs, retreats, splits).
//!
//! ## SAFETY INVARIANTS (v3 Patches)
//! 1. VAPORIZATION GUARD: directive.take() — consume once, never re-execute
//! 2. GHOST STATE CLEANUP: MergeFaction purges ALL registry entries for dissolved faction
//! 3. QUICKSELECT: SplitFaction uses select_nth_unstable_by (O(N), f32-safe)

use crate::bridges::zmq_protocol::{MacroDirective, NavigationTarget};
use crate::components::{FactionId, Position, UnitClassId};
use crate::config::{
    ActiveBuffGroup, ActiveModifier, ActiveSubFactions, ActiveZoneModifiers, AggroMaskRegistry,
    FactionBuffs, ZoneModifier, FactionTacticalOverrides, unit_registry::TacticalBehavior,
};
use crate::rules::{NavigationRule, NavigationRuleSet};
use bevy::prelude::*;

/// Holds the most recently received MacroDirective.
/// Set by ai_poll_system, consumed by directive_executor_system.
#[derive(Resource, Debug, Default)]
pub struct LatestDirective {
    pub directives: Vec<MacroDirective>,
    /// Tick when the last directive was received from Python.
    /// Used by ws_sync to determine python_connected status.
    pub last_received_tick: u64,
    /// JSON string of the last directive (for visualizer display).
    pub last_directive_json: Option<String>,
}

/// Applies the latest MacroDirective to the ECS world.
///
/// ## PATCH 1: Vaporization Guard
/// Uses `latest.directive.take()` to consume the directive.
pub fn directive_executor_system(
    mut latest: ResMut<LatestDirective>,
    mut nav_rules: ResMut<NavigationRuleSet>,
    mut int_rules: ResMut<crate::rules::InteractionRuleSet>,
    mut buffs: ResMut<FactionBuffs>,
    mut zones: ResMut<ActiveZoneModifiers>,
    mut aggro: ResMut<AggroMaskRegistry>,
    mut sub_factions: ResMut<ActiveSubFactions>,
    mut tactical_overrides: ResMut<FactionTacticalOverrides>,
    mut faction_query: Query<(Entity, &Position, &mut FactionId, &UnitClassId)>,
    buff_config: Res<crate::config::BuffConfig>,
) {
    let directives: Vec<MacroDirective> = std::mem::take(&mut latest.directives);

    if directives.is_empty() { return; }

    for directive in directives {

        match directive {
            MacroDirective::Idle => { /* no-op */ }
            MacroDirective::Hold { faction_id } => {
                nav_rules.rules.retain(|r| r.follower_faction != faction_id);
            }
    
            MacroDirective::UpdateNavigation {
                follower_faction,
                target,
            } => {
                if let Some(rule) = nav_rules
                    .rules
                    .iter_mut()
                    .find(|r| r.follower_faction == follower_faction)
                {
                    rule.target = target;
                } else {
                    nav_rules.rules.push(NavigationRule {
                        follower_faction,
                        target,
                    });
                }
            }
    
            MacroDirective::ActivateBuff {
                faction,
                modifiers,
                duration_ticks,
                targets,
            } => {
                // Cooldown check
                if buffs.cooldowns.contains_key(&faction) {
                    continue;
                }
                let active_mods: Vec<ActiveModifier> = modifiers
                    .iter()
                    .map(|m| ActiveModifier {
                        stat_index: m.stat_index,
                        modifier_type: match m.modifier_type {
                            crate::bridges::zmq_protocol::ModifierType::Multiplier => {
                                crate::config::ModifierType::Multiplier
                            }
                            crate::bridges::zmq_protocol::ModifierType::FlatAdd => {
                                crate::config::ModifierType::FlatAdd
                            }
                        },
                        value: m.value,
                    })
                    .collect();
                let group = ActiveBuffGroup {
                    modifiers: active_mods,
                    remaining_ticks: duration_ticks,
                    targets,
                };
                // Append to existing groups (faction may have multiple active buff groups)
                buffs.buffs.entry(faction).or_default().push(group);
            }
    
            MacroDirective::Retreat {
                faction,
                retreat_x,
                retreat_y,
            } => {
                let target = NavigationTarget::Waypoint {
                    x: retreat_x,
                    y: retreat_y,
                };
                if let Some(rule) = nav_rules
                    .rules
                    .iter_mut()
                    .find(|r| r.follower_faction == faction)
                {
                    rule.target = target;
                } else {
                    nav_rules.rules.push(NavigationRule {
                        follower_faction: faction,
                        target,
                    });
                }
            }
    
            MacroDirective::SetZoneModifier {
                target_faction,
                x,
                y,
                radius,
                cost_modifier,
            } => {
                zones.zones.push(ZoneModifier {
                    target_faction,
                    x,
                    y,
                    radius,
                    cost_modifier,
                    ticks_remaining: buff_config.zone_modifier_duration_ticks,
                });
            }
    
            MacroDirective::SplitFaction {
                source_faction,
                new_sub_faction,
                percentage,
                epicenter,
                class_filter,
            } => {
                let epi_vec = Vec2::new(epicenter[0], epicenter[1]);
    
                let mut candidates: Vec<(Entity, f32)> = faction_query
                    .iter()
                    .filter(|(_, _, f, class_id)| {
                        f.0 == source_faction
                            && class_filter.map_or(true, |cf| class_id.0 == cf)
                    })
                    .map(|(entity, pos, _, _)| {
                        let dist_sq = Vec2::new(pos.x, pos.y).distance_squared(epi_vec);
                        (entity, dist_sq)
                    })
                    .collect();
    
                let split_count = ((candidates.len() as f32) * percentage).round() as usize;
                if split_count == 0 || split_count > candidates.len() {
                    continue;
                }
    
                if split_count < candidates.len() {
                    candidates.select_nth_unstable_by(split_count - 1, |a, b| {
                        a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal)
                    });
                }
    
                for candidate in candidates.iter().take(split_count) {
                    if let Ok((_, _, mut faction, _)) = faction_query.get_mut(candidate.0) {
                        faction.0 = new_sub_faction;
                    }
                }
    
                if !sub_factions.factions.contains(&new_sub_faction) {
                    sub_factions.factions.push(new_sub_faction);
                }

                // Push new waypoint navigation for the sub-faction (Flanking movement)
                nav_rules.rules.push(NavigationRule {
                    follower_faction: new_sub_faction,
                    target: NavigationTarget::Waypoint { x: epicenter[0], y: epicenter[1] },
                });

                // Duplicate interaction rules from the source faction so sub-faction can fight!
                let mut int_copies = Vec::new();
                for r in &int_rules.rules {
                    if r.source_faction == source_faction {
                        let mut copy = r.clone();
                        copy.source_faction = new_sub_faction;
                        int_copies.push(copy);
                    }
                    if r.target_faction == source_faction {
                        let mut copy = r.clone();
                        copy.target_faction = new_sub_faction;
                        int_copies.push(copy);
                    }
                }
                int_rules.rules.extend(int_copies);
            }
    
            MacroDirective::MergeFaction {
                source_faction,
                target_faction,
            } => {
                for (_, _, mut faction, _) in faction_query.iter_mut() {
                    if faction.0 == source_faction {
                        faction.0 = target_faction;
                    }
                }
    
                sub_factions.factions.retain(|&f| f != source_faction);
                nav_rules
                    .rules
                    .retain(|r| r.follower_faction != source_faction);
                zones.zones.retain(|z| z.target_faction != source_faction);
                buffs.buffs.remove(&source_faction);
                tactical_overrides.overrides.remove(&source_faction);
                aggro
                    .masks
                    .retain(|&(s, t), _| s != source_faction && t != source_faction);

                // Purge sub-faction's interaction rules
                int_rules.rules.retain(|r| r.source_faction != source_faction && r.target_faction != source_faction);
            }
    
            MacroDirective::SetAggroMask {
                source_faction,
                target_faction,
                allow_combat,
            } => {
                aggro
                    .masks
                    .insert((source_faction, target_faction), allow_combat);
                aggro
                    .masks
                    .insert((target_faction, source_faction), allow_combat);
            }

            MacroDirective::SetTacticalOverride { faction, behavior } => {
                match behavior {
                    Some(payload) => {
                        let behavior = match payload {
                            crate::bridges::zmq_protocol::TacticalBehaviorPayload::Kite {
                                trigger_radius,
                                weight,
                            } => TacticalBehavior::Kite {
                                trigger_radius,
                                weight,
                            },
                            crate::bridges::zmq_protocol::TacticalBehaviorPayload::PeelForAlly {
                                target_class,
                                search_radius,
                                require_recent_damage,
                                weight,
                            } => TacticalBehavior::PeelForAlly {
                                target_class,
                                search_radius,
                                require_recent_damage,
                                weight,
                            },
                        };
                        tactical_overrides.overrides.insert(faction, vec![behavior]);
                    }
                    None => {
                        tactical_overrides.overrides.remove(&faction);
                    }
                }
            }
        }
    }
}

#[cfg(test)]
#[path = "executor_tests.rs"]
mod tests;
