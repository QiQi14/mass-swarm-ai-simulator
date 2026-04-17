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
    /// Unit class identifier. Default: 0 (generic).
    /// Used by Python for class-aware observation channels.
    #[serde(default)]
    pub unit_class_id: u32,
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

    /// Fog-of-war explored grid for the brain faction.
    /// Flattened row-major (grid_h * grid_w). 
    /// Values: 0 = unexplored, 1 = explored.
    /// None when fog of war is disabled.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fog_explored: Option<Vec<u8>>,

    /// Fog-of-war currently-visible grid for the brain faction.
    /// Flattened row-major. Values: 0 = hidden, 1 = visible now.
    /// None when fog of war is disabled.
    #[serde(skip_serializing_if = "Option::is_none")]
    pub fog_visible: Option<Vec<u8>>,

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
    pub class_density_maps: std::collections::HashMap<u32, Vec<f32>>,
    /// Effective Combat Power density maps (HP * Damage Mult)
    #[serde(default)]
    pub ecp_density_maps: std::collections::HashMap<u32, Vec<f32>>,
    #[serde(default)]
    pub intervention_active: bool,
    #[serde(default)]
    pub active_zones: Vec<ZoneModifierSnapshot>,
    #[serde(default)]
    pub active_sub_factions: Vec<u32>,
    #[serde(default)]
    pub aggro_masks: std::collections::HashMap<String, bool>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_state_snapshot_serialization_roundtrip() {
        // Arrange
        let snapshot = StateSnapshot {
            msg_type: "state_snapshot".to_string(),
            tick: 1234,
            world_size: WorldSize {
                w: 1000.0,
                h: 1000.0,
            },
            entities: vec![EntitySnapshot {
                id: 1,
                x: 150.3,
                y: 200.1,
                faction_id: 0,
                stats: vec![0.8],
                unit_class_id: 0,
            }],
            summary: SummarySnapshot {
                faction_counts: std::collections::HashMap::from([(0, 5000), (1, 200)]),
                faction_avg_stats: std::collections::HashMap::from([
                    (0, vec![0.72, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                    (1, vec![0.91, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
                ]),
            },
            explored: Some(vec![1, 2, 3]),
            visible: Some(vec![4, 5, 6]),
            fog_explored: Some(vec![1, 0, 1]),
            fog_visible: Some(vec![0, 1, 0]),
            terrain_hard: vec![100],
            terrain_soft: vec![100],
            terrain_grid_w: 1,
            terrain_grid_h: 1,
            terrain_cell_size: 20.0,
            density_maps: std::collections::HashMap::new(),
            class_density_maps: std::collections::HashMap::new(),
            ecp_density_maps: std::collections::HashMap::new(),
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
        assert_eq!(
            snapshot, deserialized,
            "StateSnapshot should survive JSON roundtrip"
        );
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
            fog_explored: None,
            fog_visible: None,
            terrain_hard: vec![],
            terrain_soft: vec![],
            terrain_grid_w: 0,
            terrain_grid_h: 0,
            terrain_cell_size: 0.0,
            density_maps: std::collections::HashMap::new(),
            class_density_maps: std::collections::HashMap::new(),
            ecp_density_maps: std::collections::HashMap::new(),
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
}
