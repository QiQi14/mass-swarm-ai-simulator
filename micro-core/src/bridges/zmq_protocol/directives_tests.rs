//! Tests for ZMQ protocol directive types.
//! Extracted from directives.rs to meet the 250-line convention.

use super::*;

#[test]
fn test_macro_action_deserialization() {
    let json = r#"{"type":"macro_action","action":"HOLD","params":{}}"#;
    let action: MacroAction = serde_json::from_str(json).unwrap();
    assert_eq!(
        action.msg_type, "macro_action",
        "type field should be 'macro_action'"
    );
    assert_eq!(action.action, "HOLD", "action should be 'HOLD'");
}

#[test]
fn test_macro_action_with_params() {
    let json = r#"{"type":"macro_action","action":"FLANK_LEFT","params":{"intensity":0.8}}"#;
    let action: MacroAction = serde_json::from_str(json).unwrap();
    assert_eq!(action.action, "FLANK_LEFT", "action should be 'FLANK_LEFT'");
    assert!(
        action.params.get("intensity").is_some(),
        "params should contain 'intensity' key"
    );
}

#[test]
fn test_macro_directive_hold_roundtrip() {
    let directive = MacroDirective::Idle;
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(directive, deserialized, "Hold directive should roundtrip");
}

#[test]
fn test_macro_directive_update_navigation_roundtrip() {
    let directive = MacroDirective::UpdateNavigation {
        follower_faction: 1,
        target: NavigationTarget::Waypoint { x: 50.0, y: 100.0 },
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "UpdateNavigation directive should roundtrip"
    );
}

#[test]
fn test_macro_directive_activate_buff_roundtrip() {
    let directive = MacroDirective::ActivateBuff {
        faction: 2,
        modifiers: vec![StatModifierPayload {
            stat_index: 0,
            modifier_type: ModifierType::Multiplier,
            value: 1.5,
        }],
        duration_ticks: 60,
        targets: Some(vec![1, 2, 3]),
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "ActivateBuff directive should roundtrip"
    );
}

#[test]
fn test_macro_directive_retreat_roundtrip() {
    let directive = MacroDirective::Retreat {
        faction: 1,
        retreat_x: 0.0,
        retreat_y: 0.0,
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "Retreat directive should roundtrip"
    );
}

#[test]
fn test_macro_directive_set_zone_modifier_roundtrip() {
    let directive = MacroDirective::SetZoneModifier {
        target_faction: 1,
        x: 10.0,
        y: 10.0,
        radius: 5.0,
        cost_modifier: -10.0,
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "SetZoneModifier directive should roundtrip"
    );
}

#[test]
fn test_macro_directive_split_faction_roundtrip() {
    let directive = MacroDirective::SplitFaction { class_filter: None,
        source_faction: 1,
        new_sub_faction: 2,
        percentage: 0.5,
        epicenter: [100.0, 200.0],
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "SplitFaction directive should roundtrip"
    );
}

#[test]
fn test_macro_directive_merge_faction_roundtrip() {
    let directive = MacroDirective::MergeFaction {
        source_faction: 2,
        target_faction: 1,
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "MergeFaction directive should roundtrip"
    );
}

#[test]
fn test_macro_directive_set_aggro_mask_roundtrip() {
    let directive = MacroDirective::SetAggroMask {
        source_faction: 1,
        target_faction: 3,
        allow_combat: false,
    };
    let json = serde_json::to_string(&directive).unwrap();
    let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
    assert_eq!(
        directive, deserialized,
        "SetAggroMask directive should roundtrip"
    );
}

#[test]
fn test_navigation_target_faction_roundtrip() {
    let target = NavigationTarget::Faction { faction_id: 10 };
    let json = serde_json::to_string(&target).unwrap();
    let deserialized: NavigationTarget = serde_json::from_str(&json).unwrap();
    assert_eq!(
        target, deserialized,
        "NavigationTarget::Faction should roundtrip"
    );
}

#[test]
fn test_navigation_target_waypoint_roundtrip() {
    let target = NavigationTarget::Waypoint { x: 55.5, y: 66.6 };
    let json = serde_json::to_string(&target).unwrap();
    let deserialized: NavigationTarget = serde_json::from_str(&json).unwrap();
    assert_eq!(
        target, deserialized,
        "NavigationTarget::Waypoint should roundtrip"
    );
}

#[test]
fn test_macro_directive_json_tag_is_directive() {
    let directive = MacroDirective::Idle;
    let json = serde_json::to_string(&directive).unwrap();
    assert!(
        json.contains("\"directive\":\"Idle\""),
        "MacroDirective JSON must use 'directive' key"
    );
}

#[test]
fn test_navigation_target_json_tag_is_type() {
    let target = NavigationTarget::Faction { faction_id: 1 };
    let json = serde_json::to_string(&target).unwrap();
    assert!(
        json.contains("\"type\":\"Faction\""),
        "NavigationTarget JSON must use 'type' key: {}",
        json
    );
}

#[test]
fn test_reset_environment_with_navigation_rules() {
    // Arrange
    let json = r#"{
        "type": "reset_environment",
        "terrain": null,
        "spawns": [],
        "navigation_rules": [
            {"follower_faction": 0, "target": {"type": "Faction", "faction_id": 1}},
            {"follower_faction": 1, "target": {"type": "Waypoint", "x": 500.0, "y": 500.0}}
        ]
    }"#;

    // Act
    let response: AiResponse = serde_json::from_str(json).unwrap();

    // Assert
    match response {
        AiResponse::ResetEnvironment {
            navigation_rules, ..
        } => {
            let rules = navigation_rules.unwrap();
            assert_eq!(rules.len(), 2, "Should have 2 navigation rules");
            assert_eq!(rules[0].follower_faction, 0);
            assert_eq!(
                rules[1].target,
                NavigationTarget::Waypoint { x: 500.0, y: 500.0 }
            );
        }
        _ => panic!("Expected ResetEnvironment"),
    }
}
