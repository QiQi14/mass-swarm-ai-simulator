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
//! - **Task:** task_07_zmq_protocol_upgrade
//! - **Contract:** implementation_plan.md → Proposed Changes → 3. Rust System Layer

use bevy::prelude::*;
use bevy_state::app::AppExtStates;
use bevy_state::prelude::*;
use std::sync::{Mutex, mpsc};

use crate::systems::directive_executor::LatestDirective;

pub mod config;
mod io_loop;
pub(crate) mod reset;
pub(crate) mod snapshot;
pub(crate) mod systems;

pub use config::{AiBridgeChannels, AiBridgeConfig, SimState};
pub use reset::{PendingReset, ResetRequest};

/// Bevy plugin that initializes the ZMQ AI bridge.
///
/// Spawns a background thread with a tokio runtime for async ZMQ I/O.
/// Registers `SimState`, `AiBridgeConfig`, `AiBridgeChannels`,
/// `LatestDirective`, and the trigger/poll systems.
pub struct ZmqBridgePlugin;

impl Plugin for ZmqBridgePlugin {
    fn build(&self, app: &mut App) {
        // Use existing config if pre-inserted (e.g., training mode overrides),
        // otherwise use default (manual play mode).
        app.init_resource::<AiBridgeConfig>();
        let config = app.world().get_resource::<AiBridgeConfig>().unwrap().clone();
        let timeout_secs = config.zmq_timeout_secs;

        let (state_tx, state_rx) = mpsc::sync_channel::<String>(1);
        let (action_tx, action_rx) = mpsc::sync_channel::<String>(1);

        std::thread::spawn(move || {
            let rt = tokio::runtime::Runtime::new().unwrap();
            rt.block_on(io_loop::zmq_io_loop(state_rx, action_tx, timeout_secs));
        });

        // LatestDirective bridges ai_poll_system (writes) → directive_executor_system (reads)
        app.init_resource::<LatestDirective>();
        app.init_resource::<PendingReset>();

        app.init_state::<SimState>()
            .insert_resource(AiBridgeChannels {
                state_tx,
                action_rx: Mutex::new(action_rx),
            })
            .add_systems(
                Update,
                (
                    systems::ai_trigger_system.run_if(in_state(SimState::Running)),
                    systems::ai_poll_system.run_if(in_state(SimState::WaitingForAI)),
                    reset::reset_environment_system,
                ),
            );
    }
}
