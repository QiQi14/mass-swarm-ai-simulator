//! # WebSocket Protocol
//!
//! DTOs for JSON serialization over the WebSocket bridge.
//!
//! ## Ownership
//! - **Task:** task_01_ws_dependencies_and_contracts
//! - **Contract:** implementation_plan.md → Phase 1 — Micro-Phase 2: WebSocket Bridge & Delta-Sync

use serde::{Deserialize, Serialize};

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
pub enum WsMessage {
    /// Delta-sync update containing entities that moved in this tick.
    SyncDelta {
        /// Current simulation tick counter.
        tick: u64,
        /// List of entities with state changes.
        moved: Vec<EntityState>,
    },
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
