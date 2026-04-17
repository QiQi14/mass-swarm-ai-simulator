use bevy::prelude::*;
use micro_core::bridges::zmq_protocol::{AbilityConfigPayload, MacroDirective};
use micro_core::config::{ActiveZoneModifiers, BuffConfig};
use micro_core::systems::directive_executor::{directive_executor_system, LatestDirective};
use serde_json::json;

#[test]
fn qa_test_ability_config_deserializes_with_duration() {
    let json_data = json!({
        "buff_cooldown_ticks": 60,
        "movement_speed_stat": 0,
        "combat_damage_stat": 1,
        "zone_modifier_duration_ticks": 240
    });

    let payload: AbilityConfigPayload = serde_json::from_value(json_data).unwrap();
    assert_eq!(payload.buff_cooldown_ticks, 60);
    assert_eq!(payload.zone_modifier_duration_ticks, 240);
}

#[test]
fn qa_test_ability_config_deserializes_without_duration() {
    let json_data = json!({
        "buff_cooldown_ticks": 60,
        "movement_speed_stat": 0,
        "combat_damage_stat": 1
    });

    // Validates backward compatibility (defaults to 120)
    let payload: AbilityConfigPayload = serde_json::from_value(json_data).unwrap();
    assert_eq!(payload.buff_cooldown_ticks, 60);
    assert_eq!(payload.zone_modifier_duration_ticks, 120);
}

#[test]
fn qa_test_buff_config_default_has_duration_120() {
    let config = BuffConfig::default();
    assert_eq!(config.zone_modifier_duration_ticks, 120);
}

#[test]
fn qa_test_directive_executor_system_uses_buff_config() {
    let mut app = App::new();
    
    // Setup resources
    let mut ld = LatestDirective::default();
    ld.directives.push(MacroDirective::SetZoneModifier {
        target_faction: 1,
        x: 0.0,
        y: 0.0,
        radius: 10.0,
        cost_modifier: -10.0,
    });
    
    app.insert_resource(ld);
    app.insert_resource(micro_core::rules::NavigationRuleSet { rules: vec![] });
    app.insert_resource(micro_core::rules::InteractionRuleSet { rules: vec![] });
    app.insert_resource(micro_core::config::FactionBuffs::default());
    app.insert_resource(ActiveZoneModifiers::default());
    app.insert_resource(micro_core::config::AggroMaskRegistry::default());
    app.insert_resource(micro_core::config::ActiveSubFactions::default());
    app.insert_resource(micro_core::config::FactionTacticalOverrides::default());
    
    // Inject a CUSTOM BuffConfig duration to verify it's wired properly, NOT 120!
    app.insert_resource(BuffConfig {
        cooldown_ticks: 0,
        movement_speed_stat: None,
        combat_damage_stat: None,
        zone_modifier_duration_ticks: 999, // Custom duration
    });
    
    app.add_systems(Update, directive_executor_system);
    app.update();
    
    let zones = app.world().get_resource::<ActiveZoneModifiers>().unwrap();
    assert_eq!(zones.zones.len(), 1);
    assert_eq!(zones.zones[0].ticks_remaining, 999, "Failed to use BuffConfig's zone_modifier_duration_ticks");
}
