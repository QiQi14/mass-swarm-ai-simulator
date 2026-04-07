//! Tests for directive_executor_system.
//! Extracted from executor.rs to meet the 300-line file size convention.

use super::*;

fn setup_app() -> App {
    let mut app = App::new();
    app.insert_resource(LatestDirective::default());
    app.insert_resource(NavigationRuleSet { rules: vec![] });
    app.insert_resource(FactionBuffs::default());
    app.insert_resource(ActiveZoneModifiers::default());
    app.insert_resource(AggroMaskRegistry::default());
    app.insert_resource(ActiveSubFactions::default());
    app.add_systems(Update, directive_executor_system);
    app
}

#[test]
fn test_latest_directive_defaults_to_none() {
    let ld = LatestDirective::default();
    assert!(
        ld.directive.is_none(),
        "LatestDirective should default to None"
    );
}

#[test]
fn test_directive_hold_is_noop() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::Hold);
    app.update();
    assert!(
        app.world()
            .get_resource::<LatestDirective>()
            .unwrap()
            .directive
            .is_none()
    );
}

#[test]
fn test_directive_update_navigation_faction() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::UpdateNavigation {
        follower_faction: 1,
        target: NavigationTarget::Faction { faction_id: 2 },
    });
    app.update();

    let nav = app.world().get_resource::<NavigationRuleSet>().unwrap();
    assert_eq!(nav.rules.len(), 1);
    assert_eq!(nav.rules[0].follower_faction, 1);
    assert_eq!(
        nav.rules[0].target,
        NavigationTarget::Faction { faction_id: 2 }
    );
}

#[test]
fn test_directive_update_navigation_waypoint() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::UpdateNavigation {
        follower_faction: 1,
        target: NavigationTarget::Waypoint { x: 50.0, y: 100.0 },
    });
    app.update();

    let nav = app.world().get_resource::<NavigationRuleSet>().unwrap();
    assert_eq!(nav.rules.len(), 1);
    assert_eq!(
        nav.rules[0].target,
        NavigationTarget::Waypoint { x: 50.0, y: 100.0 }
    );
}

#[test]
fn test_directive_activate_buff_sets_buff() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::ActivateBuff {
        faction: 1,
        modifiers: vec![crate::bridges::zmq_protocol::StatModifierPayload {
            stat_index: 0,
            modifier_type: crate::bridges::zmq_protocol::ModifierType::Multiplier,
            value: 2.0,
        }],
        duration_ticks: 60,
        targets: None,
    });
    app.update();

    let buffs = app.world().get_resource::<FactionBuffs>().unwrap();
    assert_eq!(buffs.buffs.get(&1).unwrap().len(), 1);
    assert_eq!(buffs.buffs.get(&1).unwrap()[0].modifiers[0].value, 2.0);
}

#[test]
fn test_activate_buff_cooldown_prevents_activation() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<FactionBuffs>()
        .unwrap()
        .cooldowns
        .insert(0, 10);
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::ActivateBuff {
        faction: 0,
        modifiers: vec![],
        duration_ticks: 60,
        targets: None,
    });
    app.update();
    let buffs = app.world().get_resource::<FactionBuffs>().unwrap();
    assert!(!buffs.buffs.contains_key(&0));
}

#[test]
fn test_directive_retreat_sets_waypoint() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::Retreat {
        faction: 1,
        retreat_x: 10.0,
        retreat_y: 20.0,
    });
    app.update();

    let nav = app.world().get_resource::<NavigationRuleSet>().unwrap();
    assert_eq!(nav.rules.len(), 1);
    assert_eq!(
        nav.rules[0].target,
        NavigationTarget::Waypoint { x: 10.0, y: 20.0 }
    );
}

#[test]
fn test_directive_set_zone_modifier() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::SetZoneModifier {
        target_faction: 1,
        x: 10.0,
        y: 20.0,
        radius: 5.0,
        cost_modifier: -50.0,
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
    app.world_mut()
        .spawn((Position { x: 10.0, y: 10.0 }, FactionId(1)));
    app.world_mut()
        .spawn((Position { x: 20.0, y: 20.0 }, FactionId(1)));

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::SplitFaction {
        source_faction: 1,
        new_sub_faction: 2,
        percentage: 0.5,
        epicenter: [10.0, 10.0],
    });
    app.update();

    let subs = app.world().get_resource::<ActiveSubFactions>().unwrap();
    assert!(subs.factions.contains(&2));

    let mut count1 = 0;
    let mut count2 = 0;
    let mut q = app.world_mut().query::<&FactionId>();
    for f in q.iter(app.world()) {
        if f.0 == 1 {
            count1 += 1;
        }
        if f.0 == 2 {
            count2 += 1;
        }
    }
    assert_eq!(count1, 1);
    assert_eq!(count2, 1);
}

#[test]
fn test_directive_split_faction_percentage() {
    let mut app = setup_app();
    for _ in 0..100 {
        app.world_mut()
            .spawn((Position { x: 0.0, y: 0.0 }, FactionId(1)));
    }

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::SplitFaction {
        source_faction: 1,
        new_sub_faction: 3,
        percentage: 0.3,
        epicenter: [0.0, 0.0],
    });
    app.update();

    let mut count3 = 0;
    let mut q = app.world_mut().query::<&FactionId>();
    for f in q.iter(app.world()) {
        if f.0 == 3 {
            count3 += 1;
        }
    }
    assert_eq!(count3, 30);
}

#[test]
fn test_directive_merge_faction() {
    let mut app = setup_app();
    app.world_mut()
        .spawn((Position { x: 0.0, y: 0.0 }, FactionId(2)));

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::MergeFaction {
        source_faction: 2,
        target_faction: 1,
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
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::SetAggroMask {
        source_faction: 1,
        target_faction: 2,
        allow_combat: false,
    });
    app.update();

    let aggro = app.world().get_resource::<AggroMaskRegistry>().unwrap();
    assert!(!aggro.is_combat_allowed(1, 2));
    assert!(!aggro.is_combat_allowed(2, 1));
}

// PATCH REGRESSION TESTS

#[test]
fn test_vaporization_guard_directive_consumed_once() {
    let mut app = setup_app();
    for _ in 0..100 {
        app.world_mut()
            .spawn((Position { x: 0.0, y: 0.0 }, FactionId(1)));
    }

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::SplitFaction {
        source_faction: 1,
        new_sub_faction: 3,
        percentage: 0.3,
        epicenter: [0.0, 0.0],
    });

    app.update();
    app.update();

    let mut count3 = 0;
    let mut count1 = 0;
    let mut q = app.world_mut().query::<&FactionId>();
    for f in q.iter(app.world()) {
        if f.0 == 3 {
            count3 += 1;
        }
        if f.0 == 1 {
            count1 += 1;
        }
    }
    assert_eq!(count3, 30);
    assert_eq!(count1, 70);
}

#[test]
fn test_vaporization_guard_latest_is_none_after_execution() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::Hold);
    app.update();
    assert!(
        app.world()
            .get_resource::<LatestDirective>()
            .unwrap()
            .directive
            .is_none()
    );
}

#[test]
fn test_ghost_state_merge_cleans_zones() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<ActiveZoneModifiers>()
        .unwrap()
        .zones
        .push(ZoneModifier {
            target_faction: 2,
            x: 0.0,
            y: 0.0,
            radius: 10.0,
            cost_modifier: 0.0,
            ticks_remaining: 10,
        });

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::MergeFaction {
        source_faction: 2,
        target_faction: 1,
    });
    app.update();

    let zones = app.world().get_resource::<ActiveZoneModifiers>().unwrap();
    assert_eq!(zones.zones.len(), 0);
}

#[test]
fn test_ghost_state_merge_cleans_buffs() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<FactionBuffs>()
        .unwrap()
        .buffs
        .insert(2, vec![]);

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::MergeFaction {
        source_faction: 2,
        target_faction: 1,
    });
    app.update();

    let buffs = app.world().get_resource::<FactionBuffs>().unwrap();
    assert!(!buffs.buffs.contains_key(&2));
}

#[test]
fn test_ghost_state_merge_cleans_aggro_masks() {
    let mut app = setup_app();
    app.world_mut()
        .get_resource_mut::<AggroMaskRegistry>()
        .unwrap()
        .masks
        .insert((2, 1), false);
    app.world_mut()
        .get_resource_mut::<AggroMaskRegistry>()
        .unwrap()
        .masks
        .insert((1, 2), false);

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::MergeFaction {
        source_faction: 2,
        target_faction: 1,
    });
    app.update();

    let aggro = app.world().get_resource::<AggroMaskRegistry>().unwrap();
    assert_eq!(aggro.masks.len(), 0);
}

#[test]
fn test_split_faction_quickselect_correct_count() {
    let mut app = setup_app();
    for _ in 0..100 {
        app.world_mut()
            .spawn((Position { x: 0.0, y: 0.0 }, FactionId(0)));
    }

    app.world_mut()
        .get_resource_mut::<LatestDirective>()
        .unwrap()
        .directive = Some(MacroDirective::SplitFaction {
        source_faction: 0,
        new_sub_faction: 101,
        percentage: 0.3,
        epicenter: [500.0, 500.0],
    });
    app.update();

    let mut count101 = 0;
    let mut q = app.world_mut().query::<&FactionId>();
    for f in q.iter(app.world()) {
        if f.0 == 101 {
            count101 += 1;
        }
    }
    assert_eq!(count101, 30);
}
