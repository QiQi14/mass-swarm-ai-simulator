//! # ZMQ Bridge Plugin
//!
//! Non-blocking AI communication bridge using ZeroMQ REQ/REP.
//! Uses a Bevy State Machine (`SimState`) to gate simulation systems
//! while waiting for the Python Macro-Brain to respond.
//!
//! ## Module Structure
//! - `config`   — `SimState`, `AiBridgeConfig`, `AiBridgeChannels`
//! - `io_loop`  — Background async ZMQ I/O with timeout/fallback
//! - `systems`  — Bevy ECS systems (`ai_trigger_system`, `ai_poll_system`)
//!
//! ## Ownership
//! - **Task:** task_07_zmq_bridge_plugin
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer

use bevy::prelude::*;
use bevy_state::app::AppExtStates;
use bevy_state::prelude::*;
use std::sync::{mpsc, Mutex};

pub mod config;
mod io_loop;
mod systems;

pub use config::{AiBridgeChannels, AiBridgeConfig, SimState};

/// Bevy plugin that initializes the ZMQ AI bridge.
///
/// Spawns a background thread with a tokio runtime for async ZMQ I/O.
/// Registers `SimState`, `AiBridgeConfig`, `AiBridgeChannels`, and
/// the trigger/poll systems.
pub struct ZmqBridgePlugin;

impl Plugin for ZmqBridgePlugin {
    fn build(&self, app: &mut App) {
        let config = AiBridgeConfig::default();
        let timeout_secs = config.zmq_timeout_secs;

        let (state_tx, state_rx) = mpsc::sync_channel::<String>(1);
        let (action_tx, action_rx) = mpsc::sync_channel::<String>(1);

        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(io_loop::zmq_io_loop(state_rx, action_tx, timeout_secs));
        });

        app.init_state::<SimState>()
            .insert_resource(config)
            .insert_resource(AiBridgeChannels {
                state_tx,
                action_rx: Mutex::new(action_rx),
            })
            .add_systems(
                Update,
                (
                    systems::ai_trigger_system.run_if(in_state(SimState::Running)),
                    systems::ai_poll_system.run_if(in_state(SimState::WaitingForAI)),
                ),
            );
    }
}
