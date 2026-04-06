//! # WebSocket Protocol
//!
//! DTOs for JSON serialization over the WebSocket bridge.
//!
//! ## Ownership
//! - **Task:** task_01_ws_dependencies_and_contracts
//! - **Contract:** implementation_plan.md → Phase 1 — Micro-Phase 2: WebSocket Bridge & Delta-Sync

use serde::{Deserialize, Serialize};

#[cfg(feature = "debug-telemetry")]
use crate::plugins::telemetry::PerfTelemetry;

/// Individual entity state snapshot for IPC.
#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct EntityState {
    /// Unique entity identifier.
    pub id: u32,
    /// X position in simulation units.
    pub x: f32,
    /// Y position in simulation units.
    pub y: f32,
    /// Unit velocity in X direction.
    pub dx: f32,
    /// Unit velocity in Y direction.
    pub dy: f32,
    /// Faction identifier.
    pub faction_id: u32,
    /// Anonymous stat block array.
    pub stats: Vec<f32>,
}

/// Root message type for server-to-client broadcasts.
#[derive(Serialize, Deserialize, Debug, Clone)]
#[serde(tag = "type")]
#[allow(clippy::large_enum_variant)]
pub enum WsMessage {
    /// Delta-sync update containing entities that moved in this tick.
    SyncDelta {
        /// Current simulation tick counter.
        tick: u64,
        /// List of entities with state changes.
        moved: Vec<EntityState>,
        #[serde(default)]
        removed: Vec<u32>,
        /// Present only when `debug-telemetry` feature is enabled.
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        telemetry: Option<PerfTelemetry>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        visibility: Option<VisibilitySync>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        zone_modifiers: Option<Vec<ZoneModifierSync>>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        active_sub_factions: Option<Vec<u32>>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        aggro_masks: Option<AggroMaskSync>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        ml_brain: Option<MlBrainSync>,
        #[cfg(feature = "debug-telemetry")]
        #[serde(skip_serializing_if = "Option::is_none")]
        density_heatmap: Option<std::collections::HashMap<u32, Vec<f32>>>,
    },
    /// Flow field vector data for debug visualization.
    /// Only compiled when `debug-telemetry` feature is enabled.
    #[cfg(feature = "debug-telemetry")]
    FlowFieldSync {
        target_faction: u32,
        grid_width: u32,
        grid_height: u32,
        cell_size: f32,
        /// Flat array of [dx, dy] vectors, row-major order.
        vectors: Vec<[f32; 2]>,
    },
}

#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VisibilitySync {
    pub faction_id: u32,
    pub grid_width: u32,
    pub grid_height: u32,
    pub explored: Vec<u32>,
    pub visible: Vec<u32>,
}

/// Incoming command from the Debug Visualizer (Browser → Rust).
#[derive(Deserialize, Debug, Clone)]
pub struct WsCommand {
    #[serde(rename = "type")]
    pub msg_type: String,
    pub cmd: String,
    #[serde(default)]
    pub params: serde_json::Value,
}

#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ZoneModifierSync {
    pub target_faction: u32,
    pub x: f32,
    pub y: f32,
    pub radius: f32,
    pub cost_modifier: f32,
    pub ticks_remaining: u32,
}

#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MlBrainSync {
    pub intervention_active: bool,
}

#[cfg(feature = "debug-telemetry")]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AggroMaskSync {
    pub masks: std::collections::HashMap<String, bool>,
}
