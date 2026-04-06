//! # ZMQ Protocol Data Types
//!
//! Serialization models for the AI Bridge (Rust ↔ Python) IPC.
//! Maps exactly to the schemas in `docs/ipc-protocol.md`.
//!
//! ## Ownership
//! - **Task:** task_06_zmq_protocol_cargo
//! - **Contract:** implementation_plan.md → Proposed Changes → 2. Rust Data Layer
//!
//! ## Depends On
//! - `serde`
//! - `serde_json`

use serde::{Deserialize, Serialize};

/// Entity snapshot for the AI state payload.
///
/// Maps to the `entities[]` array in the `state_snapshot` IPC message.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct EntitySnapshot {
    pub id: u32,
    pub x: f32,
    pub y: f32,
    /// Faction ID
    pub faction_id: u32,
    /// Stats
    pub stats: Vec<f32>,
}

/// Summary statistics for the neural network observation space.
///
/// Maps to the `summary` object in the `state_snapshot` IPC message.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct SummarySnapshot {
    pub faction_counts: std::collections::HashMap<u32, u32>,
    pub faction_avg_stats: std::collections::HashMap<u32, Vec<f32>>,
}

/// World size descriptor.
///
/// Maps to the `world_size` object in IPC messages.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct WorldSize {
    pub w: f32,
    pub h: f32,
}

/// Active zone modifiers for observation feedback.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct ZoneModifierSnapshot {
    pub target_faction: u32,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub cost_modifier: f32,
    pub ticks_remaining: u32,
}

/// Full state snapshot sent from Rust → Python via ZMQ REQ.
///
/// The `msg_type` field serializes as `"type"` in JSON to match
/// the IPC protocol's mandatory discriminator field.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct StateSnapshot {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub tick: u64,
    pub world_size: WorldSize,
    pub entities: Vec<EntitySnapshot>,
    pub summary: SummarySnapshot,
    pub explored: Option<Vec<u32>>,
    pub visible: Option<Vec<u32>>,
    #[serde(default)]
    pub terrain_hard: Vec<u16>,
    #[serde(default)]
    pub terrain_soft: Vec<u16>,
    #[serde(default)]
    pub terrain_grid_w: u32,
    #[serde(default)]
    pub terrain_grid_h: u32,
    #[serde(default)]
    pub terrain_cell_size: f32,
    #[serde(default)]
    pub density_maps: std::collections::HashMap<u32, Vec<f32>>,
    #[serde(default)]
    pub intervention_active: bool,
    #[serde(default)]
    pub active_zones: Vec<ZoneModifierSnapshot>,
    #[serde(default)]
    pub active_sub_factions: Vec<u32>,
    #[serde(default)]
    pub aggro_masks: std::collections::HashMap<String, bool>,
}

/// Macro action received from Python → Rust via ZMQ REP.
///
/// The `action` field contains the action vocabulary string
/// (e.g., "HOLD", "FLANK_LEFT"). The `params` field is a
/// flexible JSON object for action-specific parameters.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct MacroAction {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub action: String,
    pub params: serde_json::Value,
}

/// Navigation target: dynamic (chase a faction) or static (go to a point).
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "type")]
pub enum NavigationTarget {
    Faction { faction_id: u32 },
    Waypoint { x: f32, y: f32 },
}

/// Macro-level strategic directives from ML Brain → Rust Core.
/// 8-action vocabulary enabling all three swarm-splitting strategies:
/// - Pheromone Gravity Wells (SetZoneModifier)
/// - Dynamic Sub-Faction Tagging (SplitFaction/MergeFaction)
/// - Boids Self-Organizing Flanking (emergent, no directive needed)
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(tag = "directive")]
pub enum MacroDirective {
    Hold,

    UpdateNavigation {
        follower_faction: u32,
        target: NavigationTarget,
    },

    TriggerFrenzy {
        faction: u32,
        speed_multiplier: f32,
        duration_ticks: u32,
    },

    Retreat {
        faction: u32,
        retreat_x: f32,
        retreat_y: f32,
    },

    /// Positive cost_modifier = repel, Negative = attract
    SetZoneModifier {
        target_faction: u32,
        x: f32,
        y: f32,
        radius: f32,
        cost_modifier: f32,
    },

    /// Rust selects entities nearest to epicenter first (Quickselect O(N))
    SplitFaction {
        source_faction: u32,
        new_sub_faction: u32,
        percentage: f32,
        epicenter: [f32; 2],
    },

    MergeFaction {
        source_faction: u32,
        target_faction: u32,
    },

    SetAggroMask {
        source_faction: u32,
        target_faction: u32,
        allow_combat: bool,
    },
}

/// Discriminated union for ZMQ responses from Python.
///
/// Python can respond with either a normal directive (99% of frames)
/// or a reset command (during `SwarmEnv.reset()`).
/// Uses `type` field as the JSON discriminator.
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
pub enum AiResponse {
    /// Normal directive — maps to a MacroDirective variant.
    #[serde(rename = "macro_directive")]
    Directive {
        #[serde(flatten)]
        directive: MacroDirective,
    },

    /// Reset command — Rust rebuilds environment atomically.
    /// Sent only during SwarmEnv.reset().
    #[serde(rename = "reset_environment")]
    ResetEnvironment {
        terrain: Option<TerrainPayload>,
        spawns: Vec<SpawnConfig>,
    },
}

/// Terrain data payload for ZMQ atomic environment reset.
///
/// Contains the full terrain grid that Rust applies to `TerrainGrid`.
/// Uses the 3-tier cost encoding:
/// - Tier 0 (100-60,000): passable
/// - Tier 1 (60,001-65,534): destructible walls
/// - Tier 2 (65,535 / u16::MAX): permanent walls
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct TerrainPayload {
    pub hard_costs: Vec<u16>,
    pub soft_costs: Vec<u16>,
    pub width: u32,
    pub height: u32,
    pub cell_size: f32,
}

/// Faction spawn configuration for environment reset.
///
/// Entities are spawned around (x, y) within a `spread` radius.
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub struct SpawnConfig {
    pub faction_id: u32,
    pub count: u32,
    pub x: f32,
    pub y: f32,
    pub spread: f32,
}


// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_snapshot_serialization_roundtrip() {
        // Arrange
        let snapshot = StateSnapshot {
            msg_type: "state_snapshot".to_string(),
            tick: 1234,
            world_size: WorldSize { w: 1000.0, h: 1000.0 },
            entities: vec![
                EntitySnapshot {
                    id: 1,
                    x: 150.3,
                    y: 200.1,
                    faction_id: 0,
                    stats: vec![0.8],
                },
            ],
            summary: SummarySnapshot {
                faction_counts: std::collections::HashMap::from([(0, 5000), (1, 200)]),
                faction_avg_stats: std::collections::HashMap::from([(0, vec![0.72, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]), (1, vec![0.91, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]),
            },
            explored: Some(vec![1, 2, 3]),
            visible: Some(vec![4, 5, 6]),
            terrain_hard: vec![100],
            terrain_soft: vec![100],
            terrain_grid_w: 1,
            terrain_grid_h: 1,
            terrain_cell_size: 20.0,
            density_maps: std::collections::HashMap::new(),
            intervention_active: false,
            active_zones: vec![ZoneModifierSnapshot {
                target_faction: 0,
                x: 100.0,
                y: 100.0,
                radius: 10.0,
                cost_modifier: -50.0,
                ticks_remaining: 30,
            }],
            active_sub_factions: vec![],
            aggro_masks: std::collections::HashMap::new(),
        };

        // Act
        let json = serde_json::to_string(&snapshot).unwrap();
        let deserialized: StateSnapshot = serde_json::from_str(&json).unwrap();

        // Assert
        assert_eq!(snapshot, deserialized, "StateSnapshot should survive JSON roundtrip");
    }

    #[test]
    fn test_state_snapshot_json_has_type_field() {
        // Arrange
        let snapshot = StateSnapshot {
            msg_type: "state_snapshot".to_string(),
            tick: 0,
            world_size: WorldSize { w: 100.0, h: 100.0 },
            entities: vec![],
            summary: SummarySnapshot {
                faction_counts: std::collections::HashMap::new(),
                faction_avg_stats: std::collections::HashMap::new(),
            },
            explored: None,
            visible: None,
            terrain_hard: vec![],
            terrain_soft: vec![],
            terrain_grid_w: 0,
            terrain_grid_h: 0,
            terrain_cell_size: 0.0,
            density_maps: std::collections::HashMap::new(),
            intervention_active: false,
            active_zones: vec![],
            active_sub_factions: vec![],
            aggro_masks: std::collections::HashMap::new(),
        };

        // Act
        let json = serde_json::to_string(&snapshot).unwrap();

        // Assert
        assert!(
            json.contains("\"type\":\"state_snapshot\""),
            "JSON must use 'type' key (not 'msg_type'): {}",
            json
        );
    }

    #[test]
    fn test_macro_action_deserialization() {
        // Arrange
        let json = r#"{"type":"macro_action","action":"HOLD","params":{}}"#;

        // Act
        let action: MacroAction = serde_json::from_str(json).unwrap();

        // Assert
        assert_eq!(action.msg_type, "macro_action", "type field should be 'macro_action'");
        assert_eq!(action.action, "HOLD", "action should be 'HOLD'");
    }

    #[test]
    fn test_macro_action_with_params() {
        // Arrange
        let json = r#"{"type":"macro_action","action":"FLANK_LEFT","params":{"intensity":0.8}}"#;

        // Act
        let action: MacroAction = serde_json::from_str(json).unwrap();

        // Assert
        assert_eq!(action.action, "FLANK_LEFT", "action should be 'FLANK_LEFT'");
        assert!(
            action.params.get("intensity").is_some(),
            "params should contain 'intensity' key"
        );
    }

    #[test]
    fn test_macro_directive_hold_roundtrip() {
        let directive = MacroDirective::Hold;
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
        assert_eq!(directive, deserialized, "UpdateNavigation directive should roundtrip");
    }

    #[test]
    fn test_macro_directive_trigger_frenzy_roundtrip() {
        let directive = MacroDirective::TriggerFrenzy {
            faction: 2,
            speed_multiplier: 1.5,
            duration_ticks: 60,
        };
        let json = serde_json::to_string(&directive).unwrap();
        let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
        assert_eq!(directive, deserialized, "TriggerFrenzy directive should roundtrip");
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
        assert_eq!(directive, deserialized, "Retreat directive should roundtrip");
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
        assert_eq!(directive, deserialized, "SetZoneModifier directive should roundtrip");
    }

    #[test]
    fn test_macro_directive_split_faction_roundtrip() {
        let directive = MacroDirective::SplitFaction {
            source_faction: 1,
            new_sub_faction: 2,
            percentage: 0.5,
            epicenter: [100.0, 200.0],
        };
        let json = serde_json::to_string(&directive).unwrap();
        let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
        assert_eq!(directive, deserialized, "SplitFaction directive should roundtrip");
    }

    #[test]
    fn test_macro_directive_merge_faction_roundtrip() {
        let directive = MacroDirective::MergeFaction {
            source_faction: 2,
            target_faction: 1,
        };
        let json = serde_json::to_string(&directive).unwrap();
        let deserialized: MacroDirective = serde_json::from_str(&json).unwrap();
        assert_eq!(directive, deserialized, "MergeFaction directive should roundtrip");
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
        assert_eq!(directive, deserialized, "SetAggroMask directive should roundtrip");
    }

    #[test]
    fn test_navigation_target_faction_roundtrip() {
        let target = NavigationTarget::Faction { faction_id: 10 };
        let json = serde_json::to_string(&target).unwrap();
        let deserialized: NavigationTarget = serde_json::from_str(&json).unwrap();
        assert_eq!(target, deserialized, "NavigationTarget::Faction should roundtrip");
    }

    #[test]
    fn test_navigation_target_waypoint_roundtrip() {
        let target = NavigationTarget::Waypoint { x: 55.5, y: 66.6 };
        let json = serde_json::to_string(&target).unwrap();
        let deserialized: NavigationTarget = serde_json::from_str(&json).unwrap();
        assert_eq!(target, deserialized, "NavigationTarget::Waypoint should roundtrip");
    }

    #[test]
    fn test_macro_directive_json_tag_is_directive() {
        let directive = MacroDirective::Hold;
        let json = serde_json::to_string(&directive).unwrap();
        assert!(json.contains("\"directive\":\"Hold\""), "MacroDirective JSON must use 'directive' key");
    }

    #[test]
    fn test_navigation_target_json_tag_is_type() {
        let target = NavigationTarget::Faction { faction_id: 1 };
        let json = serde_json::to_string(&target).unwrap();
        assert!(json.contains("\"type\":\"Faction\""), "NavigationTarget JSON must use 'type' key: {}", json);
    }
}
