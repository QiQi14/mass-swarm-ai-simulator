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
}
