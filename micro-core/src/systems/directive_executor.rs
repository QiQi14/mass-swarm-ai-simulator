//! # Directive Executor System
//!
//! Consumes the latest MacroDirective and applies ECS mutations.
//!
//! ## SAFETY INVARIANTS (v3 Patches)
//! 1. VAPORIZATION GUARD: directive.take() — consume once, never re-execute
//! 2. GHOST STATE CLEANUP: MergeFaction purges ALL registry entries for dissolved faction
//! 3. QUICKSELECT: SplitFaction uses select_nth_unstable_by (O(N), f32-safe)

use bevy::prelude::*;
use crate::bridges::zmq_protocol::{MacroDirective, NavigationTarget};
use crate::rules::{NavigationRuleSet, NavigationRule};
use crate::config::{ActiveZoneModifiers, ZoneModifier, FactionSpeedBuffs, AggroMaskRegistry, ActiveSubFactions};
use crate::components::{Position, FactionId};

/// Holds the most recently received MacroDirective.
/// Set by ai_poll_system, consumed by directive_executor_system.
#[derive(Resource, Debug, Default)]
pub struct LatestDirective {
    pub directive: Option<MacroDirective>,
}

/// Applies the latest MacroDirective to the ECS world.
///
/// ## PATCH 1: Vaporization Guard
/// Uses `latest.directive.take()` to consume the directive.
pub fn directive_executor_system(
    mut latest: ResMut<LatestDirective>,
    mut nav_rules: ResMut<NavigationRuleSet>,
    mut speed_buffs: ResMut<FactionSpeedBuffs>,
    mut zones: ResMut<ActiveZoneModifiers>,
    mut aggro: ResMut<AggroMaskRegistry>,
    mut sub_factions: ResMut<ActiveSubFactions>,
    mut faction_query: Query<(Entity, &Position, &mut FactionId)>,
) {
    let Some(directive) = latest.directive.take() else { return; };

    match directive {
        MacroDirective::Hold => { /* no-op */ },

        MacroDirective::UpdateNavigation { follower_faction, target } => {
            if let Some(rule) = nav_rules.rules.iter_mut()
                .find(|r| r.follower_faction == follower_faction)
            {
                rule.target = target;
            } else {
                nav_rules.rules.push(NavigationRule {
                    follower_faction,
                    target,
                });
            }
        },

        MacroDirective::TriggerFrenzy { faction, speed_multiplier, duration_ticks } => {
            speed_buffs.buffs.insert(faction, (speed_multiplier, duration_ticks));
        },

        MacroDirective::Retreat { faction, retreat_x, retreat_y } => {
            let target = NavigationTarget::Waypoint { x: retreat_x, y: retreat_y };
            if let Some(rule) = nav_rules.rules.iter_mut()
                .find(|r| r.follower_faction == faction)
            {
                rule.target = target;
            } else {
                nav_rules.rules.push(NavigationRule {
                    follower_faction: faction,
                    target,
                });
            }
        },

        MacroDirective::SetZoneModifier { target_faction, x, y, radius, cost_modifier } => {
            zones.zones.push(ZoneModifier {
                target_faction, x, y, radius, cost_modifier,
                ticks_remaining: 120, // ~2 seconds at 60 TPS
            });
        },

        MacroDirective::SplitFaction { source_faction, new_sub_faction, percentage, epicenter } => {
            let epi_vec = Vec2::new(epicenter[0], epicenter[1]);

            let mut candidates: Vec<(Entity, f32)> = faction_query.iter()
                .filter(|(_, _, f)| f.0 == source_faction)
                .map(|(entity, pos, _)| {
                    let dist_sq = Vec2::new(pos.x, pos.y).distance_squared(epi_vec);
                    (entity, dist_sq)
                })
                .collect();

            let split_count = ((candidates.len() as f32) * percentage).round() as usize;
            if split_count == 0 || split_count > candidates.len() { return; }

            if split_count < candidates.len() {
                candidates.select_nth_unstable_by(split_count - 1, |a, b| {
                    a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal)
                });
            }

            for candidate in candidates.iter().take(split_count) {
                if let Ok((_, _, mut faction)) = faction_query.get_mut(candidate.0) {
                    faction.0 = new_sub_faction;
                }
            }

            if !sub_factions.factions.contains(&new_sub_faction) {
                sub_factions.factions.push(new_sub_faction);
            }
        },

        MacroDirective::MergeFaction { source_faction, target_faction } => {
            for (_, _, mut faction) in faction_query.iter_mut() {
                if faction.0 == source_faction {
                    faction.0 = target_faction;
                }
            }

            sub_factions.factions.retain(|&f| f != source_faction);
            nav_rules.rules.retain(|r| r.follower_faction != source_faction);
            zones.zones.retain(|z| z.target_faction != source_faction);
            speed_buffs.buffs.remove(&source_faction);
            aggro.masks.retain(|&(s, t), _| s != source_faction && t != source_faction);
        },

        MacroDirective::SetAggroMask { source_faction, target_faction, allow_combat } => {
            aggro.masks.insert((source_faction, target_faction), allow_combat);
            aggro.masks.insert((target_faction, source_faction), allow_combat);
        },
    }
}

pub fn zone_tick_system(mut zones: ResMut<ActiveZoneModifiers>) {
    zones.zones.retain_mut(|z| {
        z.ticks_remaining = z.ticks_remaining.saturating_sub(1);
        z.ticks_remaining > 0
    });
}

pub fn speed_buff_tick_system(mut buffs: ResMut<FactionSpeedBuffs>) {
    buffs.buffs.retain(|_, (_, ticks)| {
        *ticks = ticks.saturating_sub(1);
        *ticks > 0
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_app() -> App {
        let mut app = App::new();
        app.insert_resource(LatestDirective::default());
        app.insert_resource(NavigationRuleSet { rules: vec![] });
        app.insert_resource(FactionSpeedBuffs::default());
        app.insert_resource(ActiveZoneModifiers::default());
        app.insert_resource(AggroMaskRegistry::default());
        app.insert_resource(ActiveSubFactions::default());
        app.add_systems(Update, directive_executor_system);
        app
    }

    #[test]
    fn test_latest_directive_defaults_to_none() {
        let ld = LatestDirective::default();
        assert!(ld.directive.is_none(), "LatestDirective should default to None");
    }

    #[test]
    fn test_directive_hold_is_noop() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::Hold);
        app.update();
        // Since Hold is no-op, checking Vaporization trick is enough
        assert!(app.world().get_resource::<LatestDirective>().unwrap().directive.is_none());
    }

    #[test]
    fn test_directive_update_navigation_faction() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::UpdateNavigation {
            follower_faction: 1,
            target: NavigationTarget::Faction { faction_id: 2 }
        });
        app.update();

        let nav = app.world().get_resource::<NavigationRuleSet>().unwrap();
        assert_eq!(nav.rules.len(), 1);
        assert_eq!(nav.rules[0].follower_faction, 1);
        assert_eq!(nav.rules[0].target, NavigationTarget::Faction { faction_id: 2 });
    }

    #[test]
    fn test_directive_update_navigation_waypoint() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::UpdateNavigation {
            follower_faction: 1,
            target: NavigationTarget::Waypoint { x: 50.0, y: 100.0 }
        });
        app.update();

        let nav = app.world().get_resource::<NavigationRuleSet>().unwrap();
        assert_eq!(nav.rules.len(), 1);
        assert_eq!(nav.rules[0].target, NavigationTarget::Waypoint { x: 50.0, y: 100.0 });
    }

    #[test]
    fn test_directive_trigger_frenzy_sets_buff() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::TriggerFrenzy {
            faction: 1,
            speed_multiplier: 2.0,
            duration_ticks: 60
        });
        app.update();

        let buffs = app.world().get_resource::<FactionSpeedBuffs>().unwrap();
        assert_eq!(buffs.buffs.get(&1), Some(&(2.0, 60)));
    }

    #[test]
    fn test_directive_retreat_sets_waypoint() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::Retreat {
            faction: 1,
            retreat_x: 10.0,
            retreat_y: 20.0
        });
        app.update();

        let nav = app.world().get_resource::<NavigationRuleSet>().unwrap();
        assert_eq!(nav.rules.len(), 1);
        assert_eq!(nav.rules[0].target, NavigationTarget::Waypoint { x: 10.0, y: 20.0 });
    }

    #[test]
    fn test_directive_set_zone_modifier() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::SetZoneModifier {
            target_faction: 1,
            x: 10.0,
            y: 20.0,
            radius: 5.0,
            cost_modifier: -50.0
        });
        app.update();

        let zones = app.world().get_resource::<ActiveZoneModifiers>().unwrap();
        assert_eq!(zones.zones.len(), 1);
        assert_eq!(zones.zones[0].target_faction, 1);
        assert_eq!(zones.zones[0].cost_modifier, -50.0);
    }

    #[test]
    fn test_directive_split_faction_by_epicenter() {
        let mut app = setup_app();
        
        // Setup entities
        app.world_mut().spawn((Position { x: 10.0, y: 10.0 }, FactionId(1))); // close
        app.world_mut().spawn((Position { x: 20.0, y: 20.0 }, FactionId(1))); // far
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::SplitFaction {
            source_faction: 1,
            new_sub_faction: 2,
            percentage: 0.5,
            epicenter: [10.0, 10.0]
        });
        app.update();

        let subs = app.world().get_resource::<ActiveSubFactions>().unwrap();
        assert!(subs.factions.contains(&2));

        let mut count1 = 0;
        let mut count2 = 0;
        let mut q = app.world_mut().query::<&FactionId>();
        for f in q.iter(app.world()) {
            if f.0 == 1 { count1 += 1; }
            if f.0 == 2 { count2 += 1; }
        }
        
        assert_eq!(count1, 1);
        assert_eq!(count2, 1);
    }

    #[test]
    fn test_directive_split_faction_percentage() {
        let mut app = setup_app();
        
        for _ in 0..100 {
            app.world_mut().spawn((Position { x: 0.0, y: 0.0 }, FactionId(1)));
        }
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::SplitFaction {
            source_faction: 1,
            new_sub_faction: 3,
            percentage: 0.3,
            epicenter: [0.0, 0.0]
        });
        app.update();

        let mut count3 = 0;
        let mut q = app.world_mut().query::<&FactionId>();
        for f in q.iter(app.world()) {
            if f.0 == 3 { count3 += 1; }
        }
        
        assert_eq!(count3, 30);
    }

    #[test]
    fn test_directive_merge_faction() {
        let mut app = setup_app();
        app.world_mut().spawn((Position { x: 0.0, y: 0.0 }, FactionId(2)));
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::MergeFaction {
            source_faction: 2,
            target_faction: 1
        });
        app.update();

        let mut q = app.world_mut().query::<&FactionId>();
        for f in q.iter(app.world()) {
            assert_eq!(f.0, 1);
        }
    }

    #[test]
    fn test_directive_set_aggro_mask_disables_combat() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::SetAggroMask {
            source_faction: 1,
            target_faction: 2,
            allow_combat: false
        });
        app.update();

        let aggro = app.world().get_resource::<AggroMaskRegistry>().unwrap();
        assert_eq!(aggro.is_combat_allowed(1, 2), false);
        assert_eq!(aggro.is_combat_allowed(2, 1), false);
    }

    // PATCH REGRESSION TESTS

    #[test]
    fn test_vaporization_guard_directive_consumed_once() {
        let mut app = setup_app();
        for _ in 0..100 {
            app.world_mut().spawn((Position { x: 0.0, y: 0.0 }, FactionId(1)));
        }
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::SplitFaction {
            source_faction: 1,
            new_sub_faction: 3,
            percentage: 0.3,
            epicenter: [0.0, 0.0]
        });
        
        app.update(); // first tick
        app.update(); // second tick

        let mut count3 = 0;
        let mut count1 = 0;
        let mut q = app.world_mut().query::<&FactionId>();
        for f in q.iter(app.world()) {
            if f.0 == 3 { count3 += 1; }
            if f.0 == 1 { count1 += 1; }
        }
        
        assert_eq!(count3, 30);
        assert_eq!(count1, 70);
    }

    #[test]
    fn test_vaporization_guard_latest_is_none_after_execution() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::Hold);
        app.update();
        assert!(app.world().get_resource::<LatestDirective>().unwrap().directive.is_none());
    }

    #[test]
    fn test_ghost_state_merge_cleans_zones() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<ActiveZoneModifiers>().unwrap().zones.push(ZoneModifier {
            target_faction: 2, x: 0.0, y: 0.0, radius: 10.0, cost_modifier: 0.0, ticks_remaining: 10
        });
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::MergeFaction { source_faction: 2, target_faction: 1 });
        app.update();
        
        let zones = app.world().get_resource::<ActiveZoneModifiers>().unwrap();
        assert_eq!(zones.zones.len(), 0);
    }

    #[test]
    fn test_ghost_state_merge_cleans_speed_buffs() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<FactionSpeedBuffs>().unwrap().buffs.insert(2, (2.0, 10));
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::MergeFaction { source_faction: 2, target_faction: 1 });
        app.update();
        
        let buffs = app.world().get_resource::<FactionSpeedBuffs>().unwrap();
        assert!(!buffs.buffs.contains_key(&2));
    }

    #[test]
    fn test_ghost_state_merge_cleans_aggro_masks() {
        let mut app = setup_app();
        app.world_mut().get_resource_mut::<AggroMaskRegistry>().unwrap().masks.insert((2, 1), false);
        app.world_mut().get_resource_mut::<AggroMaskRegistry>().unwrap().masks.insert((1, 2), false);
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::MergeFaction { source_faction: 2, target_faction: 1 });
        app.update();
        
        let aggro = app.world().get_resource::<AggroMaskRegistry>().unwrap();
        assert_eq!(aggro.masks.len(), 0);
    }

    #[test]
    fn test_split_faction_quickselect_correct_count() {
        let mut app = setup_app();
        for _ in 0..100 {
            app.world_mut().spawn((Position { x: 0.0, y: 0.0 }, FactionId(0)));
        }
        
        app.world_mut().get_resource_mut::<LatestDirective>().unwrap().directive = Some(MacroDirective::SplitFaction {
            source_faction: 0,
            new_sub_faction: 101,
            percentage: 0.3,
            epicenter: [500.0, 500.0]
        });
        app.update();

        let mut count101 = 0;
        let mut q = app.world_mut().query::<&FactionId>();
        for f in q.iter(app.world()) {
            if f.0 == 101 { count101 += 1; }
        }
        assert_eq!(count101, 30);
    }
}
