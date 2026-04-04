//! # ZMQ Bridge — Configuration & State
//!
//! Data types for AI bridge timing, channel communication, and
//! simulation state gating. These are the shared resources used
//! by the plugin, systems, and background I/O loop.
//!
//! ## Ownership
//! - **Task:** task_07_zmq_bridge_plugin
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer

use bevy::prelude::*;
use bevy_state::prelude::*;
use serde::{Deserialize, Serialize};
use std::sync::{mpsc, Mutex};

/// Simulation state for AI communication gating.
///
/// Systems like `movement_system` only run in `Running` state.
/// When `WaitingForAI`, the simulation pauses movement but keeps
/// ticking (tick counter, WS sync, logging continue).
#[derive(States, Debug, Clone, PartialEq, Eq, Hash, Default)]
pub enum SimState {
    #[default]
    Running,
    WaitingForAI,
}

/// Configuration for AI bridge timing and resilience.
///
/// Public and serializable so the Debug Visualizer GUI can
/// reconfigure it at runtime via the WS command bridge.
#[derive(Resource, Debug, Clone, Serialize, Deserialize)]
pub struct AiBridgeConfig {
    /// Send state to Python every N ticks (default: 30 → ~2 Hz at 60 TPS).
    pub send_interval_ticks: u64,
    /// Timeout in seconds for ZMQ send/recv before falling back to
    /// the default HOLD action. Prevents simulation hang on AI disconnect.
    pub zmq_timeout_secs: u64,
}

impl Default for AiBridgeConfig {
    fn default() -> Self {
        Self {
            send_interval_ticks: 30,
            zmq_timeout_secs: 5,
        }
    }
}

/// Channel endpoints for Bevy ↔ background thread communication.
///
/// Capacity is 1 (bounded) — the bridge processes one REQ/REP cycle at a time.
/// `action_rx` is wrapped in `Mutex` because `mpsc::Receiver` is `Send`
/// but not `Sync`, and Bevy requires all `Resource` types to be `Send + Sync`.
#[derive(Resource)]
pub struct AiBridgeChannels {
    /// Send serialized state snapshots TO the background ZMQ thread.
    pub state_tx: mpsc::SyncSender<String>,
    /// Receive macro action responses FROM the background ZMQ thread.
    pub action_rx: Mutex<mpsc::Receiver<String>>,
}

// ── Tests ──────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_ai_bridge_config_default() {
        // Arrange
        let config = AiBridgeConfig::default();

        // Assert
        assert_eq!(config.send_interval_ticks, 30);
        assert_eq!(config.zmq_timeout_secs, 5);
    }

    #[test]
    fn test_ai_bridge_config_serialization_roundtrip() {
        // Arrange
        let original = AiBridgeConfig::default();

        // Act
        let json = serde_json::to_string(&original).unwrap();
        let deserialized: AiBridgeConfig = serde_json::from_str(&json).unwrap();

        // Assert
        assert_eq!(original.send_interval_ticks, deserialized.send_interval_ticks);
        assert_eq!(original.zmq_timeout_secs, deserialized.zmq_timeout_secs);
    }
}
